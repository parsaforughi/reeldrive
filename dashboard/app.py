"""FastAPI admin dashboard for Reeldrive."""

import hashlib
import hmac
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from bot.config import settings
from bot.db.engine import async_session, init_db
from bot.db.models import ActivityLog, BotUser, UserConnection, WatchlistEntry
from bot.services.apify import apify_downloader
from bot.services.client_pool import client_pool

STATIC_DIR = Path(__file__).parent / "static"
SESSION_COOKIE = "reeldrive_admin"
SESSION_DAYS = 7


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Reeldrive Dashboard", lifespan=lifespan)


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


@app.get("/api/users")
async def api_users(_: None = Depends(require_admin)):
    async with async_session() as session:
        users = (
            await session.execute(
                select(BotUser).order_by(desc(BotUser.last_seen_at)).limit(500)
            )
        ).scalars().all()
        connections = {
            c.telegram_id: c
            for c in (
                await session.execute(select(UserConnection))
            ).scalars().all()
        }

    out = []
    for u in users:
        conn = connections.get(u.telegram_id)
        out.append(
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "name": " ".join(
                    x for x in [u.first_name, u.last_name] if x
                ).strip()
                or "—",
                "plan": u.subscription_plan,
                "expires": u.subscription_expires_at.isoformat()
                if u.subscription_expires_at
                else None,
                "downloads": u.download_count,
                "commands": u.command_count,
                "first_seen": u.first_seen_at.isoformat() if u.first_seen_at else None,
                "last_seen": u.last_seen_at.isoformat() if u.last_seen_at else None,
                "ig_connected": conn.status if conn else None,
                "ig_username": conn.instagram_username if conn else None,
                "blocked": u.is_blocked,
            }
        )
    return out


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
    return [
        {
            "id": r.id,
            "telegram_id": r.telegram_id,
            "event_type": r.event_type,
            "detail": r.detail,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@app.patch("/api/users/{telegram_id}/subscription")
async def patch_subscription(
    telegram_id: int,
    body: SubscriptionBody,
    _: None = Depends(require_admin),
):
    plan = body.plan.lower()
    if plan not in ("free", "pro", "premium"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    expires = None
    if plan != "free" and body.days:
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            days=body.days
        )

    async with async_session() as session:
        user = await session.get(BotUser, telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.subscription_plan = plan
        user.subscription_expires_at = expires
        session.add(
            ActivityLog(
                telegram_id=telegram_id,
                event_type="admin",
                detail=f"subscription → {plan}",
            )
        )
        await session.commit()
    return {"ok": True, "plan": plan, "expires": expires.isoformat() if expires else None}


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
            "expires": u.subscription_expires_at.isoformat()
            if u.subscription_expires_at
            else None,
            "downloads": u.download_count,
        }
        for u in rows
    ]


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
