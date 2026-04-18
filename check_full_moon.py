#!/usr/bin/env python3
\"\"\"
check_full_moon.py – Returns whether a full moon is occurring today or tomorrow.

Usage:
    python check_full_moon.py          # prints JSON to stdout
    python check_full_moon.py --bool   # prints only True/False

Exit codes:
    0 = full moon today or tomorrow
    1 = no full moon today or tomorrow

Designed to be called by schedulers, cron jobs, or other automation.
\"\"\"

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta

import ephem


def check_full_moon(reference_utc: datetime | None = None) -> dict:
    \"\"\"
    Check if a full moon falls on today or tomorrow (UTC dates).

    Returns a dict:
      {
        "full_moon_today": bool,
        "full_moon_tomorrow": bool,
        "is_full_moon_soon": bool,          # True if either of the above
        "next_full_moon_utc": "ISO string",
        "today_utc": "YYYY-MM-DD",
        "tomorrow_utc": "YYYY-MM-DD",
      }
    \"\"\"
    now = reference_utc or datetime.now(timezone.utc)
    today = now.date()
    tomorrow = today + timedelta(days=1)

    # Walk backwards to find the full moon nearest to now.
    # We check: next full moon from (now - 1 day) and next full moon from now.
    check_start = now - timedelta(days=1)
    nearest_candidates = []

    # Previous full moon (search from 30 days ago)
    prev_full = ephem.previous_full_moon(ephem.Date(now))
    prev_full_dt = ephem.Date(prev_full).datetime().replace(tzinfo=timezone.utc)
    nearest_candidates.append(prev_full_dt)

    # Next full moon
    next_full = ephem.next_full_moon(ephem.Date(now))
    next_full_dt = ephem.Date(next_full).datetime().replace(tzinfo=timezone.utc)
    nearest_candidates.append(next_full_dt)

    full_moon_today = any(c.date() == today for c in nearest_candidates)
    full_moon_tomorrow = any(c.date() == tomorrow for c in nearest_candidates)

    return {
        "full_moon_today": full_moon_today,
        "full_moon_tomorrow": full_moon_tomorrow,
        "is_full_moon_soon": full_moon_today or full_moon_tomorrow,
        "next_full_moon_utc": next_full_dt.isoformat(),
        "today_utc": today.isoformat(),
        "tomorrow_utc": tomorrow.isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Check if full moon is today or tomorrow.")
    parser.add_argument("--bool", action="store_true", help="Print only True/False")
    parser.add_argument("--date", type=str, default=None,
                        help="Override reference date (ISO format, e.g. 2026-03-03T12:00:00)")
    args = parser.parse_args()

    ref = None
    if args.date:
        ref = datetime.fromisoformat(args.date).replace(tzinfo=timezone.utc)

    result = check_full_moon(ref)

    if args.bool:
        print(result["is_full_moon_soon"])
    else:
        print(json.dumps(result, indent=2))

    sys.exit(0 if result["is_full_moon_soon"] else 1)


if __name__ == "__main__":
    main()
