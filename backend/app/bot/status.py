"""Lifecycle state of the Telegram bot, kept in memory for GET /bot/status.

Only codes and exception class names are stored: Telegram errors can echo the token in their
message and in request URLs, so nothing else is ever recorded.
"""

import enum
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from app.models.base import utcnow


class BotState(str, enum.Enum):
    DISABLED = "disabled"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass(frozen=True)
class LastError:
    type: str
    at: datetime


@dataclass(frozen=True)
class BotStatusSnapshot:
    status: BotState = BotState.STOPPED
    # A code (missing_token, missing_user_id) or an exception class name; never a message
    reason: str | None = None
    started_at: datetime | None = None
    last_message_sent_at: datetime | None = None
    last_error: LastError | None = None


class BotStatus:
    """Holder of the current snapshot. Snapshots are immutable and replaced whole, so readers on
    other threads never see a half-written state; writers all run on the event loop."""

    def __init__(self, clock: Callable[[], datetime] = utcnow) -> None:
        self._clock = clock
        self._snapshot = BotStatusSnapshot()

    @property
    def snapshot(self) -> BotStatusSnapshot:
        return self._snapshot

    def disabled(self, reason: str) -> None:
        self._snapshot = replace(self._snapshot, status=BotState.DISABLED, reason=reason)

    def running(self) -> None:
        self._snapshot = replace(
            self._snapshot, status=BotState.RUNNING, reason=None, started_at=self._clock()
        )

    def failed(self, error_name: str) -> None:
        self._snapshot = replace(self._snapshot, status=BotState.FAILED, reason=error_name)

    def stopped(self) -> None:
        self._snapshot = replace(self._snapshot, status=BotState.STOPPED, reason=None)

    def polling_error(self, error: BaseException) -> None:
        """error_callback of the updater; PTB calls it again for as long as the outage lasts."""
        self._snapshot = replace(
            self._snapshot, last_error=LastError(type=type(error).__name__, at=self._clock())
        )
