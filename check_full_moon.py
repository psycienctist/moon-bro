#!/usr/bin/env python3
"""
check_full_moon.py – Returns whether a full moon is occurring today or tomorrow.
Supports sending a Telegram alert if a full moon is detected.

Usage:
    python check_full_moon.py          # prints JSON to stdout
    python check_full_moon.py --bool   # prints only True/False
    python check_full_moon.py --alert  # sends Telegram alert if full moon soon
"""

import argparse
import json
import sys
import os
import requests
from datetime import datetime, timezone, timedelta

import ephem


def check_full_moon(reference_utc: datetime | None = None) -> dict:
    now = reference_utc or datetime.now(timezone.utc)
    today = now.date()
    tomorrow = today + timedelta(days=1)

    # walk backwards to find candidates
    prev_full = ephem.previous_full_moon(ephem.Date(now))
    prev_full_dt = ephem.Date(prev_full).datetime().replace(tzinfo=timezone.utc)
    
    next_full = ephem.next_full_moon(ephem.Date(now))
    next_full_dt = ephem.Date(next_full).datetime().replace(tzinfo=timezone.utc)
    
    candidates = [prev_full_dt, next_full_dt]

    full_today = any(c.date() == today for c in candidates)
    full_tomorrow = any(c.date() == tomorrow for c in candidates)

    return {
        "full_moon_today": full_today,
        "full_moon_tomorrow": full_tomorrow,
        "is_full_moon_soon": full_today or full_tomorrow,
        "next_full_moon_utc": next_full_dt.isoformat(),
        "today_utc": today.isoformat(),
        "tomorrow_utc": tomorrow.isoformat(),
    }

def send_telegram_alert(result):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return

    msg = "🌕 *Full Moon Alert!* \n\n"
    if result["full_moon_today"]:
        msg += "The moon reaches peak fullness *TODAY*! 🌑✨"
    else:
        msg += "A Full Moon is rising *TOMORROW*! Prepare your intentions. 🕯️🌙"
    
    msg += f"\n\nTrack it live: [Lunatick App](https://moon-bro.streamlit.app)"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
        resp.raise_for_status()
        print("Telegram alert sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def main():
    parser = argparse.ArgumentParser(description="Check if full moon is today or tomorrow.")
    parser.add_argument("--bool", action="store_true", help="Print only True/False")
    parser.add_argument("--alert", action="store_true", help="Send Telegram alert if full moon soon")
    parser.add_argument("--date", type=str, default=None, help="ISO date override")
    args = parser.parse_args()

    ref = None
    if args.date:
        ref = datetime.fromisoformat(args.date).replace(tzinfo=timezone.utc)

    result = check_full_moon(ref)

    if args.alert and result["is_full_moon_soon"]:
        send_telegram_alert(result)

    if args.bool:
        print(result["is_full_moon_soon"])
    else:
        print(json.dumps(result, indent=2))

    sys.exit(0 if result["is_full_moon_soon"] else 1)

if __name__ == "__main__":
    main()
