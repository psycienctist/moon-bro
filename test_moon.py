"""Tests for Moon Management app components and check_full_moon script."""

import json
import math
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import ephem
import pytest


# ---------------------------------------------------------------------------
# Import the check_full_moon module
# ---------------------------------------------------------------------------
sys.path.insert(0, "/root/workspace/moon-bro")
from check_full_moon import check_full_moon


# ---------------------------------------------------------------------------
# Tests for check_full_moon
# ---------------------------------------------------------------------------

class TestCheckFullMoon:
    """Tests for the check_full_moon function."""

    def test_returns_expected_keys(self):
        result = check_full_moon()
        expected_keys = {
            "full_moon_today", "full_moon_tomorrow", "is_full_moon_soon",
            "next_full_moon_utc", "today_utc", "tomorrow_utc",
        }
        assert set(result.keys()) == expected_keys

    def test_boolean_types(self):
        result = check_full_moon()
        assert isinstance(result["full_moon_today"], bool)
        assert isinstance(result["full_moon_tomorrow"], bool)
        assert isinstance(result["is_full_moon_soon"], bool)

    def test_is_full_moon_soon_is_or_of_today_tomorrow(self):
        result = check_full_moon()
        assert result["is_full_moon_soon"] == (
            result["full_moon_today"] or result["full_moon_tomorrow"]
        )

    def test_known_full_moon_date_march_3_2026(self):
        """March 3, 2026 is a known full moon (Worm Moon / Total Lunar Eclipse)."""
        ref = datetime(2026, 3, 3, 12, 0, 0, tzinfo=timezone.utc)
        result = check_full_moon(ref)
        assert result["full_moon_today"] is True
        assert result["is_full_moon_soon"] is True

    def test_known_full_moon_eve_march_2_2026(self):
        """March 2, 2026 – the full moon is tomorrow (March 3)."""
        ref = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
        result = check_full_moon(ref)
        assert result["full_moon_tomorrow"] is True
        assert result["is_full_moon_soon"] is True

    def test_no_full_moon_mid_month(self):
        """March 15, 2026 – nowhere near a full moon."""
        ref = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = check_full_moon(ref)
        assert result["full_moon_today"] is False
        assert result["full_moon_tomorrow"] is False
        assert result["is_full_moon_soon"] is False

    def test_known_full_moon_may_1_2026(self):
        """May 1, 2026 is a full moon (Flower Moon)."""
        ref = datetime(2026, 5, 1, 18, 0, 0, tzinfo=timezone.utc)
        result = check_full_moon(ref)
        assert result["full_moon_today"] is True

    def test_known_full_moon_august_28_2026(self):
        """August 28, 2026 – Partial Lunar Eclipse / Sturgeon Moon."""
        ref = datetime(2026, 8, 28, 6, 0, 0, tzinfo=timezone.utc)
        result = check_full_moon(ref)
        assert result["full_moon_today"] is True

    def test_next_full_moon_is_in_future(self):
        """next_full_moon_utc should always be >= now."""
        now = datetime.now(timezone.utc)
        result = check_full_moon(now)
        next_fm = datetime.fromisoformat(result["next_full_moon_utc"])
        assert next_fm >= now - timedelta(hours=1)  # small tolerance

    def test_dates_are_iso_format(self):
        result = check_full_moon()
        datetime.fromisoformat(result["next_full_moon_utc"])
        datetime.fromisoformat(result["today_utc"])
        datetime.fromisoformat(result["tomorrow_utc"])


# ---------------------------------------------------------------------------
# Tests for CLI invocation
# ---------------------------------------------------------------------------

class TestCheckFullMoonCLI:
    """Test the script as a CLI tool."""

    def test_json_output(self):
        proc = subprocess.run(
            [sys.executable, "/root/workspace/moon-bro/check_full_moon.py",
             "--date", "2026-03-03T12:00:00"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0  # full moon day → exit 0
        data = json.loads(proc.stdout)
        assert data["full_moon_today"] is True

    def test_bool_output(self):
        proc = subprocess.run(
            [sys.executable, "/root/workspace/moon-bro/check_full_moon.py",
             "--bool", "--date", "2026-03-03T12:00:00"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == "True"

    def test_exit_code_1_no_full_moon(self):
        proc = subprocess.run(
            [sys.executable, "/root/workspace/moon-bro/check_full_moon.py",
             "--date", "2026-03-15T12:00:00"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 1
        data = json.loads(proc.stdout)
        assert data["is_full_moon_soon"] is False


# ---------------------------------------------------------------------------
# Tests for app helper functions (imported inline to avoid Streamlit startup)
# ---------------------------------------------------------------------------

class TestAppHelpers:
    """Test the core calculation logic used by app.py."""

    def test_ephem_moon_illumination_full_moon(self):
        """At full moon, illumination should be very high."""
        obs = ephem.Observer()
        obs.lat = "0"
        obs.lon = "0"
        obs.date = ephem.Date(datetime(2026, 3, 3, 11, 38, 0))
        moon = ephem.Moon(obs)
        assert moon.phase > 95  # should be ~99-100%

    def test_ephem_moon_illumination_new_moon(self):
        """At new moon, illumination should be very low."""
        # New moon around Jan 18, 2026
        next_new = ephem.next_new_moon(ephem.Date(datetime(2026, 1, 15)))
        obs = ephem.Observer()
        obs.lat = "0"
        obs.lon = "0"
        obs.date = next_new
        moon = ephem.Moon(obs)
        assert moon.phase < 5

    def test_zodiac_sign_calculation(self):
        """Ecliptic longitude should map to a valid zodiac index (0-11)."""
        obs = ephem.Observer()
        obs.lat = "0"
        obs.lon = "0"
        obs.date = ephem.Date(datetime(2026, 4, 18, 12, 0, 0))
        moon = ephem.Moon(obs)
        ecl = ephem.Ecliptic(moon)
        lon_deg = math.degrees(float(ecl.lon)) % 360
        sign_index = int(lon_deg / 30)
        assert 0 <= sign_index <= 11

    def test_phase_fraction_range(self):
        """Phase fraction from elongation should be 0-1."""
        obs = ephem.Observer()
        obs.lat = "0"
        obs.lon = "0"
        for day_offset in range(0, 30):
            obs.date = ephem.Date(datetime(2026, 4, 1, 12, 0, 0) + timedelta(days=day_offset))
            moon = ephem.Moon(obs)
            elong = float(moon.elong)
            if elong < 0:
                elong += 2 * math.pi
            phase_frac = elong / (2 * math.pi)
            assert 0 <= phase_frac <= 1, f"Phase fraction out of range on day offset {day_offset}"

    def test_next_full_moon_is_after_reference(self):
        """ephem.next_full_moon should return a date after the input."""
        ref = ephem.Date(datetime(2026, 4, 18, 12, 0, 0))
        nfm = ephem.next_full_moon(ref)
        assert nfm > ref


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
