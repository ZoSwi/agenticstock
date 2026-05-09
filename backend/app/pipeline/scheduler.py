from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.pipeline.daily_job import run_daily, run_live_feed_only


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _daily_time() -> tuple[int, int]:
    raw = os.environ.get("PIPELINE_DAILY_REFRESH_TIME", "05:15").strip()
    try:
        hh, mm = raw.split(":", 1)
        hour, minute = int(hh), int(mm)
    except Exception as exc:
        raise ValueError("PIPELINE_DAILY_REFRESH_TIME must be HH:MM (24h)") from exc
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("PIPELINE_DAILY_REFRESH_TIME must be HH:MM (24h)")
    return hour, minute


def _next_daily_run(now: datetime, hour: int, minute: int) -> datetime:
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


async def run_scheduler() -> None:
    tz_name = os.environ.get("PIPELINE_TIMEZONE", "America/New_York")
    tz = ZoneInfo(tz_name)
    hour, minute = _daily_time()
    live_feed_enabled = _env_bool("LIVE_FEED_ENABLED", True)
    live_feed_minutes = max(1, int(os.environ.get("LIVE_FEED_REFRESH_MINUTES", "15")))

    now = datetime.now(tz)
    next_daily = _next_daily_run(now, hour, minute)
    next_feed = now if live_feed_enabled else None

    print(
        f"[pipeline-scheduler] timezone={tz_name} daily_at={hour:02d}:{minute:02d} "
        f"live_feed_enabled={live_feed_enabled} live_feed_minutes={live_feed_minutes}"
    )

    while True:
        now = datetime.now(tz)
        did_work = False

        if now >= next_daily:
            print(f"[pipeline-scheduler] running daily refresh at {now.isoformat()}")
            try:
                result = await run_daily()
                print(f"[pipeline-scheduler] daily refresh result={result}")
            except Exception as exc:
                print(f"[pipeline-scheduler] daily refresh failed: {exc}")
            next_daily = _next_daily_run(datetime.now(tz), hour, minute)
            did_work = True

        if live_feed_enabled and next_feed is not None and now >= next_feed:
            print(f"[pipeline-scheduler] running live feed pull at {now.isoformat()}")
            try:
                result = await run_live_feed_only()
                print(f"[pipeline-scheduler] live feed result={result}")
            except Exception as exc:
                print(f"[pipeline-scheduler] live feed pull failed: {exc}")
            next_feed = datetime.now(tz) + timedelta(minutes=live_feed_minutes)
            did_work = True

        if did_work:
            continue

        sleep_until = next_daily
        if live_feed_enabled and next_feed is not None and next_feed < sleep_until:
            sleep_until = next_feed
        sleep_seconds = max(5.0, (sleep_until - datetime.now(tz)).total_seconds())
        await asyncio.sleep(sleep_seconds)


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
