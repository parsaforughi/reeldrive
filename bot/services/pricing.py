"""Pro subscription pricing — Stars and Toman tiers."""

from bot.config import settings

PRO_DURATION_OPTIONS: tuple[dict[str, int | str], ...] = (
    {"days": 30, "months": 1, "label": "۳۰ روز (۱ ماه)"},
    {"days": 60, "months": 2, "label": "۶۰ روز (۲ ماه)"},
    {"days": 90, "months": 3, "label": "۹۰ روز (۳ ماه)"},
    {"days": 180, "months": 6, "label": "۱۸۰ روز (۶ ماه)"},
    {"days": 365, "months": 12, "label": "۳۶۵ روز (۱ سال)"},
)

_ALLOWED_DAYS = frozenset(p["days"] for p in PRO_DURATION_OPTIONS)


def plan_by_days(days: int) -> dict[str, int | str] | None:
    for plan in PRO_DURATION_OPTIONS:
        if plan["days"] == days:
            return plan
    return None


def plan_stars(days: int) -> int:
    plan = plan_by_days(days)
    if not plan:
        return settings.pro_stars_price
    return settings.pro_stars_price * int(plan["months"])


def plan_tomans(days: int) -> int:
    plan = plan_by_days(days)
    if not plan:
        return settings.pro_toman_monthly
    return settings.pro_toman_monthly * int(plan["months"])


def shop_plans_payload() -> list[dict]:
    return [
        {
            "days": p["days"],
            "months": p["months"],
            "label": p["label"],
            "stars": plan_stars(int(p["days"])),
            "tomans": plan_tomans(int(p["days"])),
        }
        for p in PRO_DURATION_OPTIONS
    ]


def is_allowed_plan_days(days: int) -> bool:
    return days in _ALLOWED_DAYS
