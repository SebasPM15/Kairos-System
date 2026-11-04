from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.weeks import WeekBucket, current_week_start, week_buckets, window_start

GUAYAQUIL = ZoneInfo("America/Guayaquil")  # UTC-5, no DST
NEW_YORK = ZoneInfo("America/New_York")


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_sunday_2359_local_stays_in_the_week_and_monday_0000_starts_the_next():
    # 2026-11-01 is a Sunday; local 23:59 is 04:59 UTC on Monday 2026-11-02
    now = utc(2026, 11, 4, 12)
    sunday_end = utc(2026, 11, 2, 4, 59)
    monday_start = utc(2026, 11, 2, 5, 0)

    buckets = week_buckets([sunday_end, monday_start], now, 2, GUAYAQUIL)

    assert buckets == [
        WeekBucket(date(2026, 10, 26), 1),
        WeekBucket(date(2026, 11, 2), 1),
    ]


def test_empty_weeks_are_zero_and_the_window_is_oldest_first():
    now = utc(2026, 11, 4, 12)  # Wednesday

    buckets = week_buckets([utc(2026, 11, 3, 15)], now, 4, GUAYAQUIL)

    assert [b.week_start for b in buckets] == [
        date(2026, 10, 12), date(2026, 10, 19), date(2026, 10, 26), date(2026, 11, 2),
    ]
    assert [b.count for b in buckets] == [0, 0, 0, 1]


def test_timestamps_outside_the_window_are_ignored():
    now = utc(2026, 11, 4, 12)
    older = now - timedelta(weeks=10)
    future = now + timedelta(weeks=2)

    buckets = week_buckets([older, future], now, 3, GUAYAQUIL)

    assert [b.count for b in buckets] == [0, 0, 0]


def test_long_window_covers_a_full_year_of_distinct_mondays():
    now = utc(2026, 11, 4, 12)

    buckets = week_buckets([], now, 52, GUAYAQUIL)

    assert len(buckets) == 52
    assert all(b.week_start.weekday() == 0 for b in buckets)
    assert len({b.week_start for b in buckets}) == 52
    assert buckets[-1].week_start == current_week_start(now, GUAYAQUIL)


def test_week_across_the_new_york_fall_back_change_keeps_its_boundaries():
    # DST ends Sunday 2026-11-01 at 02:00 local: Monday 2026-11-02 00:00 EST is 05:00 UTC,
    # while Monday 2026-10-26 00:00 EDT is 04:00 UTC
    now = utc(2026, 11, 4, 12)
    last_of_week = utc(2026, 11, 2, 4, 59)   # Sunday 23:59 EST
    first_of_next = utc(2026, 11, 2, 5, 0)   # Monday 00:00 EST
    edt_monday = utc(2026, 10, 26, 4, 0)     # Monday 00:00 EDT, first instant of its week
    before_edt_monday = utc(2026, 10, 26, 3, 59)

    buckets = week_buckets(
        [last_of_week, first_of_next, edt_monday, before_edt_monday], now, 3, NEW_YORK
    )

    assert buckets == [
        WeekBucket(date(2026, 10, 19), 1),
        WeekBucket(date(2026, 10, 26), 2),
        WeekBucket(date(2026, 11, 2), 1),
    ]


def test_window_start_is_local_monday_midnight_in_utc_across_dst():
    now = utc(2026, 11, 4, 12)

    # Oldest week starts Monday 2026-10-26 00:00 EDT = 04:00 UTC; the current one is EST
    assert window_start(now, 2, NEW_YORK) == utc(2026, 10, 26, 4, 0)
    assert window_start(now, 1, NEW_YORK) == utc(2026, 11, 2, 5, 0)
