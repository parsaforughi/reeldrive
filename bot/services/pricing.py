"""Pro subscription pricing — Stars and Toman tiers.

Every plan is priced as ``cost × months × markup`` where cost is
``settings.pro_cost_usd_monthly`` and markup stays within 2–2.5×: the
1-month plan carries the full 2.5× and longer plans trade margin for a
discount, bottoming out at 2× for a year.
"""

import math

from bot.config import settings

PRO_DURATION_OPTIONS: tuple[dict[str, int | float | str], ...] = (
    {"days": 30, "months": 1, "markup": 2.5, "label": "۳۰ روز (۱ ماه)"},
    {"days": 60, "months": 2, "markup": 2.4, "label": "۶۰ روز (۲ ماه)"},
    {"days": 90, "months": 3, "markup": 2.3, "label": "۹۰ روز (۳ ماه)"},
    {"days": 180, "months": 6, "markup": 2.15, "label": "۱۸۰ روز (۶ ماه)"},
    {"days": 365, "months": 12, "markup": 2.0, "label": "۳۶۵ روز (۱ سال)"},
)

_TOMAN_ROUNDING = 1000

_ALLOWED_DAYS = frozenset(p["days"] for p in PRO_DURATION_OPTIONS)


def plan_by_days(days: int) -> dict[str, int | float | str] | None:
    for plan in PRO_DURATION_OPTIONS:
        if plan["days"] == days:
            return plan
    return None


def _plan_price_usd(days: int) -> float:
    plan = plan_by_days(days) or PRO_DURATION_OPTIONS[0]
    # round() guards against float noise (e.g. 1.3 * 2.5 = 3.2500000000000004)
    # tipping a ceil() below into the next unit.
    return round(settings.pro_cost_usd_monthly * int(plan["months"]) * float(plan["markup"]), 6)


def plan_stars(days: int) -> int:
    return math.ceil(round(_plan_price_usd(days) / settings.stars_payout_usd, 6))


def plan_tomans(days: int) -> int:
    tomans = _plan_price_usd(days) * settings.usd_toman_rate
    return math.ceil(round(tomans / _TOMAN_ROUNDING, 6)) * _TOMAN_ROUNDING


def monthly_stars() -> int:
    return plan_stars(30)


def monthly_tomans() -> int:
    return plan_tomans(30)


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
