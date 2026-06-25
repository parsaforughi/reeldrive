"""Progress bar + ETA for long-running video analysis."""

from __future__ import annotations

import time

# stage name -> weight (must sum to 100)
STAGE_WEIGHTS: list[tuple[str, int]] = [
    ("download", 8),
    ("technical", 17),
    ("audio", 20),
    ("frames", 25),
    ("visual", 30),
]

_STAGE_ORDER = [s[0] for s in STAGE_WEIGHTS]
_INITIAL_ETA = 50  # seconds, before first measurement


def ai_error_key(http_status: int) -> str:
    if http_status in (401, 403):
        return "ai_auth_failed"
    if http_status == 429:
        return "ai_rate_limit"
    return "ai_api_error"


def progress_bar(pct: int, width: int = 10) -> str:
    pct = max(0, min(100, pct))
    filled = round(pct * width / 100)
    return "▓" * filled + "░" * (width - filled)


class AnalysisProgress:
    def __init__(self) -> None:
        self._start = time.monotonic()
        self._last_pct = 0

    def pct_at_stage(self, stage: str) -> int:
        """Progress % when a stage *starts*."""
        if stage not in _STAGE_ORDER:
            return self._last_pct
        idx = _STAGE_ORDER.index(stage)
        done = sum(w for name, w in STAGE_WEIGHTS[:idx])
        self._last_pct = min(99, done)
        return self._last_pct

    def eta_seconds(self, pct: int) -> int:
        if pct < 5:
            return _INITIAL_ETA
        elapsed = time.monotonic() - self._start
        if elapsed < 1:
            return _INITIAL_ETA
        est_total = elapsed / (pct / 100.0)
        remaining = est_total - elapsed
        return max(5, int(remaining))
