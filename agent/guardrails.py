"""Multi-layer browsing guardrail for the Pinterest scraping loop."""

from __future__ import annotations

import time


class BrowsingGuardrail:
    """Single source of truth for all 'stop browsing' decisions.

    Limits enforced:
      1. max_pins        — absolute cap on pins collected
      2. max_scrolls     — cap on scroll iterations
      3. session_timeout — wall-clock seconds since start
      4. error_streak    — consecutive errors before abort
      5. stale_scrolls   — consecutive scrolls that yield no new pins
    """

    def __init__(
        self,
        max_pins: int = 40,
        max_scrolls: int = 8,
        session_timeout_s: int = 180,
        max_error_streak: int = 5,
        max_stale_scrolls: int = 2,
    ) -> None:
        self.max_pins = max_pins
        self.max_scrolls = max_scrolls
        self.session_timeout_s = session_timeout_s
        self.max_error_streak = max_error_streak
        self.max_stale_scrolls = max_stale_scrolls

        self._start_time = time.monotonic()
        self._scroll_count = 0
        self._pins_collected = 0
        self._error_streak = 0
        self._stale_scroll_count = 0
        self._last_pin_count = 0

    # ── Counters called by the scraping loop ─────────────────────────

    def record_scroll(self, current_pin_count: int) -> None:
        """Call once per scroll iteration with the running pin count."""
        self._scroll_count += 1
        new_pins = current_pin_count - self._last_pin_count
        if new_pins == 0:
            self._stale_scroll_count += 1
        else:
            self._stale_scroll_count = 0
        self._last_pin_count = current_pin_count

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
        if self._scroll_count >= self.max_scrolls:
            return f"scroll cap reached ({self.max_scrolls})"
        if self.elapsed_s >= self.session_timeout_s:
            return f"session timeout ({self.session_timeout_s}s)"
        if self._error_streak >= self.max_error_streak:
            return (
                f"error circuit breaker ({self._error_streak} consecutive errors)"
            )
        if self._stale_scroll_count >= self.max_stale_scrolls:
            return (
                f"stale feed ({self._stale_scroll_count} scrolls with no new pins)"
            )
        return None

    @property
    def elapsed_s(self) -> float:
        return time.monotonic() - self._start_time

    def status_line(self) -> str:
        return (
            f"pins={self._pins_collected}/{self.max_pins}  "
            f"scrolls={self._scroll_count}/{self.max_scrolls}  "
            f"elapsed={self.elapsed_s:.0f}s/{self.session_timeout_s}s  "
            f"errors_streak={self._error_streak}  "
            f"stale_scrolls={self._stale_scroll_count}"
        )
