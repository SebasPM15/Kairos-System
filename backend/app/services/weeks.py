from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class WeekBucket:
    week_start: date
    count: int


def current_week_start(now: datetime, tz: ZoneInfo) -> date:
    """Monday of the local week containing `now`."""
    local = now.astimezone(tz).date()
    return local - timedelta(days=local.weekday())


def window_start(now: datetime, weeks: int, tz: ZoneInfo) -> datetime:
    """UTC instant of local Monday 00:00 of the oldest week in the window."""
    first = current_week_start(now, tz) - timedelta(weeks=weeks - 1)
    # Built from the local date, so a DST change inside the window cannot shift it
    return datetime.combine(first, time.min, tzinfo=tz).astimezone(UTC)


def week_buckets(
    timestamps: Iterable[datetime], now: datetime, weeks: int, tz: ZoneInfo
) -> list[WeekBucket]:
    """Count timestamps per local Monday-to-Sunday week, oldest first, zeros included.

    The last bucket is the current week, which is still partial. Timestamps outside the
    window (older, or after the current week) are ignored.
    """
    current = current_week_start(now, tz)
    starts = [current - timedelta(weeks=offset) for offset in range(weeks - 1, -1, -1)]
    counts: Counter[date] = Counter()
    for stamp in timestamps:
        local = stamp.astimezone(tz).date()
        counts[local - timedelta(days=local.weekday())] += 1
    return [WeekBucket(start, counts.get(start, 0)) for start in starts]
