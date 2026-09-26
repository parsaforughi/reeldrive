from bot.config import settings
from bot.services.pricing import PRO_DURATION_OPTIONS, plan_stars, plan_tomans


def _cost_tomans(months: int) -> float:
    return settings.pro_cost_usd_monthly * settings.usd_toman_rate * months


def _cost_stars(months: int) -> float:
    return settings.pro_cost_usd_monthly * months / settings.stars_payout_usd


def test_every_plan_is_priced_between_2x_and_2_5x_cost():
    for plan in PRO_DURATION_OPTIONS:
        days, months = int(plan["days"]), int(plan["months"])
        toman_ratio = plan_tomans(days) / _cost_tomans(months)
        stars_ratio = plan_stars(days) / _cost_stars(months)
        # Rounding up to the next 1000 toman / Star may nudge a hair over.
        assert 1.999 <= toman_ratio <= 2.51, (days, toman_ratio)
        assert 1.999 <= stars_ratio <= 2.51, (days, stars_ratio)


def test_longer_plans_are_cheaper_per_month():
    per_month = [
        plan_tomans(int(p["days"])) / int(p["months"]) for p in PRO_DURATION_OPTIONS
    ]
    assert per_month == sorted(per_month, reverse=True)


def test_current_prices():
    assert [plan_tomans(int(p["days"])) for p in PRO_DURATION_OPTIONS] == [
        748_000,
        1_436_000,
        2_064_000,
        3_858_000,
        7_176_000,
    ]
    assert [plan_stars(int(p["days"])) for p in PRO_DURATION_OPTIONS] == [
        250,
        480,
        690,
        1290,
        2400,
    ]
