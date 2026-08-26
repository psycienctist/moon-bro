from datetime import datetime, timezone

import cosmic_cards


def test_historical_dst_conversion():
    summer = cosmic_cards._local_to_utc("2020-07-01", "12:00", timezone_name="America/New_York")
    winter = cosmic_cards._local_to_utc("2020-01-01", "12:00", timezone_name="America/New_York")
    assert summer == datetime(2020, 7, 1, 16, 0, tzinfo=timezone.utc)
    assert winter == datetime(2020, 1, 1, 17, 0, tzinfo=timezone.utc)


def test_timezone_and_ascendant_are_resolved():
    assert cosmic_cards._timezone_for_coordinates(40.7128, -74.0060) == "America/New_York"
    dt_utc = cosmic_cards._local_to_utc("1990-06-15", "12:00", timezone_name="America/New_York")
    chart = cosmic_cards._chart(dt_utc, 40.7128, -74.0060)
    assert chart["has_rising"] is True
    assert chart["rising_sign"] == "Virgo"


def test_postal_code_lookup_returns_confirmable_results():
    results = cosmic_cards._geocode_place("10001")
    assert results
    assert all(result["timezone"] for result in results)
    assert all(-90 <= result["lat"] <= 90 for result in results)
    assert all(-180 <= result["lon"] <= 180 for result in results)


if __name__ == "__main__":
    test_historical_dst_conversion()
    test_timezone_and_ascendant_are_resolved()
    test_postal_code_lookup_returns_confirmable_results()
    print("Astrology and postal-code regression checks passed.")
