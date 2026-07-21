"""FastAPI admin dashboard for Reeldrive."""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import desc, func, or_, select

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import LabeledPrice

from bot.config import settings
from bot.db.engine import async_session, db_ping, init_db
from bot.db.migrate import maybe_migrate_sqlite_to_postgres
from bot.db.models import ActivityLog, BotUser, UserConnection, WatchlistEntry
from bot.handlers.payments import PRO_PAYLOAD, _payload
from bot.i18n import require_user_lang, t
from bot.services.apify import apify_downloader
from bot.services.pricing import (
    is_allowed_plan_days,
    plan_by_days,
    plan_stars,
    shop_plans_payload,
)
from bot.services.client_pool import client_pool
from bot.services.following_access import (
    current_card_holder_name,
    current_support_card,
    set_support_card,
)
from bot.services.subscription import (
    PRO_PLANS,
    get_bot_user,
    grant_pro,
    is_ai_unlimited,
    is_plan_active,
    subscription_status_line,
)
from bot.time_utils import to_iso_utc
from bot.webapp_auth import validate_init_data

STATIC_DIR = Path(__file__).parent / "static"
SESSION_COOKIE = "reeldrive_admin"
SESSION_DAYS = 7
logger = logging.getLogger(__name__)
_db_ready = False


def _sign_token(raw: str) -> str:
    return hmac.new(
        settings.dashboard_secret.encode(),
        raw.encode(),
        hashlib.sha256,
    ).hexdigest()


def _make_session() -> str:
    raw = secrets.token_urlsafe(24)
    return f"{raw}.{_sign_token(raw)}"


def _verify_session(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    raw, sig = token.rsplit(".", 1)
    return hmac.compare_digest(sig, _sign_token(raw))


async def require_admin(request: Request) -> None:
    if not _verify_session(request.cookies.get(SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _parse_meta(meta_json: str | None) -> dict:
    if not meta_json:
        return {}
    try:
        return json.loads(meta_json)
    except json.JSONDecodeError:
        return {}


def _log_user_label(
    telegram_id: int | None,
    meta: dict,
    users_by_id: dict[int, BotUser],
) -> str | None:
    if meta.get("display"):
        return meta["display"]
    if meta.get("username"):
        return f"@{meta['username']}"
    if telegram_id and telegram_id in users_by_id:
        u = users_by_id[telegram_id]
        if u.username:
            return f"@{u.username}"
        name = " ".join(x for x in [u.first_name, u.last_name] if x).strip()
        if name:
            return f"{name} ({telegram_id})"
    if telegram_id:
        return str(telegram_id)
    return None


async def _setup_database() -> None:
    global _db_ready
    try:
        await init_db()
        await maybe_migrate_sqlite_to_postgres()
        _db_ready = True
        logger.info("Dashboard database ready")
    except Exception:
        logger.exception("Dashboard database setup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do not block HTTP /health while Postgres connects (Railway healthcheck).
    app.state.db_task = asyncio.create_task(_setup_database())
    yield


app = FastAPI(title="Reeldrive Dashboard", lifespan=lifespan)


@app.get("/health")
async def health():
    db_ok = await db_ping() if _db_ready else False
    return {
        "ok": True,
        "service": "reeldrive-dashboard",
        "database": "postgres" if settings.database_is_postgres else "sqlite",
        "database_ok": db_ok,
        "db_setup_complete": _db_ready,
        "data_dir": str(settings.persistent_data_dir),
    }


class LoginBody(BaseModel):
    password: str


class SubscriptionBody(BaseModel):
    plan: str
    days: int | None = 30


@app.post("/api/login")
async def login(body: LoginBody, response: Response):
    if not hmac.compare_digest(body.password, settings.dashboard_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = _make_session()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        max_age=SESSION_DAYS * 86400,
        samesite="lax",
    )
    return {"ok": True}


@app.post("/api/logout")
async def logout(response: Response, _: None = Depends(require_admin)):
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/stats")
async def api_stats(_: None = Depends(require_admin)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    day_ago = now - timedelta(days=1)

    async with async_session() as session:
        total_users = await session.scalar(select(func.count(BotUser.telegram_id)))
        pro_users = await session.scalar(
            select(func.count(BotUser.telegram_id)).where(
                BotUser.subscription_plan != "free"
            )
        )
        connected = await session.scalar(
            select(func.count(UserConnection.telegram_id)).where(
                UserConnection.status == "connected"
            )
        )
        downloads = await session.scalar(
            select(func.coalesce(func.sum(BotUser.download_count), 0))
        )
        today_logs = await session.scalar(
            select(func.count(ActivityLog.id)).where(ActivityLog.created_at >= day_ago)
        )
        today_downloads = await session.scalar(
            select(func.count(ActivityLog.id)).where(
                ActivityLog.event_type == "download",
                ActivityLog.created_at >= day_ago,
            )
        )

    return {
        "total_users": total_users or 0,
        "pro_users": pro_users or 0,
        "connected_pages": connected or 0,
        "total_downloads": int(downloads or 0),
        "activity_24h": today_logs or 0,
        "downloads_24h": today_downloads or 0,
        "system": {
            "apify": apify_downloader.ready,
            "ig_service": client_pool.service_ready,
            "ig_bridge": client_pool.bridge_ready,
            "bot_name": settings.bot_name,
        },
    }


@app.get("/api/users/lookup")
async def api_users_lookup(username: str, _: None = Depends(require_admin)):
    handle = (username or "").strip().lstrip("@")
    if not handle:
        raise HTTPException(status_code=400, detail="Username required")
    async with async_session() as session:
        telegram_id = await session.scalar(
            select(BotUser.telegram_id).where(func.lower(BotUser.username) == handle.lower())
        )
    if telegram_id is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"telegram_id": telegram_id}


@app.get("/api/users")
async def api_users(
    page: int = 1,
    page_size: int = 50,
    q: str = "",
    _: None = Depends(require_admin),
):
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    q = (q or "").strip()

    async with async_session() as session:
        stmt = select(BotUser)
        count_stmt = select(func.count(BotUser.telegram_id))
        if q:
            conds = [BotUser.username.ilike(f"%{q}%")]
            if q.lstrip("-").isdigit():
                conds.append(BotUser.telegram_id == int(q))
            cond = or_(*conds)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = await session.scalar(count_stmt) or 0
        users = (
            await session.execute(
                stmt.order_by(desc(BotUser.last_seen_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        ids = [u.telegram_id for u in users]
        connections: dict[int, UserConnection] = {}
        if ids:
            connections = {
                c.telegram_id: c
                for c in (
                    await session.execute(
                        select(UserConnection).where(UserConnection.telegram_id.in_(ids))
                    )
                ).scalars().all()
            }

    items = []
    for u in users:
        conn = connections.get(u.telegram_id)
        items.append(
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "name": " ".join(
                    x for x in [u.first_name, u.last_name] if x
                ).strip()
                or "—",
                "plan": u.subscription_plan,
                "expires": to_iso_utc(u.subscription_expires_at),
                "downloads": u.download_count,
                "commands": u.command_count,
                "first_seen": to_iso_utc(u.first_seen_at),
                "last_seen": to_iso_utc(u.last_seen_at),
                "ig_connected": conn.status if conn else None,
                "ig_username": conn.instagram_username if conn else None,
                "blocked": u.is_blocked,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/logs")
async def api_logs(limit: int = 150, _: None = Depends(require_admin)):
    async with async_session() as session:
        rows = (
            await session.execute(
                select(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(
                    min(limit, 500)
                )
            )
        ).scalars().all()
        ids = {r.telegram_id for r in rows if r.telegram_id}
        users_by_id: dict[int, BotUser] = {}
        if ids:
            users_by_id = {
                u.telegram_id: u
                for u in (
                    await session.execute(
                        select(BotUser).where(BotUser.telegram_id.in_(ids))
                    )
                ).scalars().all()
            }

    out = []
    for r in rows:
        meta = _parse_meta(r.meta_json)
        out.append(
            {
                "id": r.id,
                "telegram_id": r.telegram_id,
                "username": meta.get("username"),
                "user_label": _log_user_label(r.telegram_id, meta, users_by_id),
                "event_type": r.event_type,
                "detail": r.detail,
                "created_at": to_iso_utc(r.created_at),
            }
        )
    return out


@app.patch("/api/users/{telegram_id}/subscription")
async def patch_subscription(
    telegram_id: int,
    body: SubscriptionBody,
    _: None = Depends(require_admin),
):
    plan = body.plan.lower()
    if plan not in ("free", "pro"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    if plan == "free":
        async with async_session() as session:
            user = await session.get(BotUser, telegram_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.subscription_plan = "free"
            user.subscription_expires_at = None
            session.add(
                ActivityLog(
                    telegram_id=telegram_id,
                    event_type="admin",
                    detail="subscription → free",
                )
            )
            await session.commit()
        return {"ok": True, "plan": "free", "expires": None}

    days = max(1, body.days or 30)
    expires = await grant_pro(telegram_id, days=days)
    async with async_session() as session:
        session.add(
            ActivityLog(
                telegram_id=telegram_id,
                event_type="admin",
                detail=f"subscription → pro (+{days}d)",
            )
        )
        await session.commit()
    return {"ok": True, "plan": "pro", "expires": to_iso_utc(expires)}


@app.get("/api/subscriptions")
async def api_subscriptions(_: None = Depends(require_admin)):
    async with async_session() as session:
        rows = (
            await session.execute(
                select(BotUser)
                .where(BotUser.subscription_plan != "free")
                .order_by(desc(BotUser.subscription_expires_at))
            )
        ).scalars().all()
    return [
        {
            "telegram_id": u.telegram_id,
            "username": u.username,
            "plan": u.subscription_plan,
            "expires": to_iso_utc(u.subscription_expires_at),
            "downloads": u.download_count,
        }
        for u in rows
    ]


class CardBody(BaseModel):
    card: str
    holder: str


@app.get("/api/settings/card")
async def api_get_card(_: None = Depends(require_admin)):
    return {
        "card": await current_support_card(),
        "holder": await current_card_holder_name(),
    }


@app.post("/api/settings/card")
async def api_set_card(body: CardBody, _: None = Depends(require_admin)):
    card = (body.card or "").strip()
    holder = (body.holder or "").strip()
    if not card.isdigit() or not (12 <= len(card) <= 19):
        raise HTTPException(status_code=400, detail="شماره کارت نامعتبر است (فقط رقم، ۱۲ تا ۱۹ رقم).")
    if not holder:
        raise HTTPException(status_code=400, detail="نام صاحب کارت را وارد کن.")
    await set_support_card(card, holder)
    return {"ok": True, "card": card, "holder": holder}


class BroadcastBody(BaseModel):
    message: str


_broadcast_state: dict = {
    "running": False,
    "total": 0,
    "sent": 0,
    "failed": 0,
    "started_at": None,
    "finished_at": None,
}


async def _run_broadcast(telegram_ids: list[int], text: str) -> None:
    bot = Bot(token=settings.telegram_bot_token)
    try:
        for telegram_id in telegram_ids:
            try:
                await bot.send_message(telegram_id, text)
                _broadcast_state["sent"] += 1
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                try:
                    await bot.send_message(telegram_id, text)
                    _broadcast_state["sent"] += 1
                except Exception:
                    _broadcast_state["failed"] += 1
            except TelegramForbiddenError:
                # User blocked/kicked the bot — mark it so future broadcasts
                # and the users table skip them.
                _broadcast_state["failed"] += 1
                async with async_session() as session:
                    user = await session.get(BotUser, telegram_id)
                    if user:
                        user.is_blocked = True
                        await session.commit()
            except Exception:
                logger.warning(
                    "Broadcast send failed for %s", telegram_id, exc_info=True
                )
                _broadcast_state["failed"] += 1
            # Stays comfortably under Telegram's ~30 msg/sec bot rate limit.
            await asyncio.sleep(0.05)
    finally:
        await bot.session.close()
        _broadcast_state["running"] = False
        _broadcast_state["finished_at"] = datetime.now(timezone.utc).isoformat()


@app.post("/api/broadcast")
async def api_broadcast(body: BroadcastBody, _: None = Depends(require_admin)):
    text = (body.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="متن پیام خالی است.")
    if _broadcast_state["running"]:
        raise HTTPException(status_code=409, detail="یک پیام همگانی در حال ارسال است.")

    async with async_session() as session:
        ids = (
            await session.scalars(
                select(BotUser.telegram_id).where(BotUser.is_blocked.is_(False))
            )
        ).all()

    _broadcast_state.update(
        running=True,
        total=len(ids),
        sent=0,
        failed=0,
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
    )
    asyncio.create_task(_run_broadcast(list(ids), text))
    return {"ok": True, "total": len(ids)}


@app.get("/api/broadcast/status")
async def api_broadcast_status(_: None = Depends(require_admin)):
    return _broadcast_state


class WebAppBody(BaseModel):
    init_data: str


class WebAppInvoiceBody(BaseModel):
    init_data: str
    days: int = 30


def _shop_user_from_init(body: WebAppBody) -> dict:
    user = validate_init_data(body.init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid init data")
    return user


@app.get("/shop")
async def shop_page():
    path = STATIC_DIR / "shop.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Shop not found")
    return FileResponse(path)


@app.post("/api/shop/info")
async def api_shop_info(body: WebAppBody):
    tg_user = _shop_user_from_init(body)
    telegram_id = int(tg_user["id"])
    username = tg_user.get("username")

    lang = await require_user_lang(telegram_id)
    user = await get_bot_user(telegram_id)
    vip = await is_ai_unlimited(telegram_id, username)
    status = await subscription_status_line(
        user, vip, lang, telegram_id=telegram_id, username=username
    )
    pro_active = bool(
        is_plan_active(user) and user and user.subscription_plan in PRO_PLANS
    )
    support = settings.payment_support_username.lstrip("@")

    return {
        "telegram_id": telegram_id,
        "bot_name": settings.bot_name,
        "pro_stars_monthly": settings.pro_stars_price,
        "pro_toman_monthly": settings.pro_toman_monthly,
        "plans": shop_plans_payload(),
        "pro_active": pro_active,
        "status_html": f"<strong>وضعیت:</strong> {status}",
        "card_url": f"https://t.me/{support}",
        "stars_enabled": settings.stars_payment_enabled,
    }


@app.post("/api/shop/invoice")
async def api_shop_invoice(body: WebAppInvoiceBody):
    if not settings.stars_payment_enabled:
        raise HTTPException(status_code=403, detail="پرداخت Stars غیرفعال است.")

    if not is_allowed_plan_days(body.days):
        raise HTTPException(status_code=400, detail="مدت زمان نامعتبر است.")

    tg_user = _shop_user_from_init(body)
    telegram_id = int(tg_user["id"])
    lang = await require_user_lang(telegram_id)
    plan = plan_by_days(body.days)
    stars = plan_stars(body.days)

    user = await get_bot_user(telegram_id)
    if is_plan_active(user) and user and user.subscription_plan in PRO_PLANS:
        raise HTTPException(status_code=409, detail="Pro قبلاً فعال است.")

    bot = Bot(token=settings.telegram_bot_token)
    try:
        link = await bot.create_invoice_link(
            title=t("pro_invoice_title", lang),
            description=t(
                "pro_invoice_desc",
                lang,
                days=body.days,
                name=settings.bot_name,
            ),
            payload=_payload(PRO_PAYLOAD, telegram_id, body.days),
            provider_token="",
            currency="XTR",
            prices=[
                LabeledPrice(
                    label=t("pro_price_label", lang, days=body.days),
                    amount=stars,
                )
            ],
        )
    finally:
        await bot.session.close()

    return {"invoice_link": link, "stars": stars, "days": body.days, "label": plan["label"] if plan else ""}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
