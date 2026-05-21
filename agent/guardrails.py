"""Multi-layer browsing guardrail for the Pinterest scraping loop."""

from __future__ import annotations

import time


class BrowsingGuardrail:
    """Single source of truth for all 'stop browsing' decisions.

    Limits enforced:
      1. max_pins        — absolute cap on pins collected
      2. session_timeout — wall-clock seconds since start
      3. error_streak    — consecutive errors before abort
    """

    def __init__(
        self,
        max_pins: int = 40,
        session_timeout_s: int = 180,
        max_error_streak: int = 5,
    ) -> None:
        self.max_pins = max_pins
        self.session_timeout_s = session_timeout_s
        self.max_error_streak = max_error_streak

        self._start_time = time.monotonic()
        self._pins_collected = 0
        self._error_streak = 0

    # ── Counters called by the scoring loop ──────────────────────────

    def record_pin_collected(self) -> None:
        self._pins_collected += 1
        self._error_streak = 0

    def record_error(self) -> None:
        self._error_streak += 1

    # ── Stop-signal checks ───────────────────────────────────────────

    @property
    def should_stop(self) -> bool:
        return self.stop_reason is not None

    @property
    def stop_reason(self) -> str | None:
        if self._pins_collected >= self.max_pins:
            return f"pin cap reached ({self.max_pins})"
        if self.elapsed_s >= self.session_timeout_s:
            return f"session timeout ({self.session_timeout_s}s)"
        if self._error_streak >= self.max_error_streak:
            return (
                f"error circuit breaker ({self._error_streak} consecutive errors)"
            )
        return None

    @property
    def elapsed_s(self) -> float:
        return time.monotonic() - self._start_time

    def status_line(self) -> str:
        return (
            f"pins={self._pins_collected}/{self.max_pins}  "
            f"elapsed={self.elapsed_s:.0f}s/{self.session_timeout_s}s  "
            f"errors_streak={self._error_streak}"
        )
