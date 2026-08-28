"""Regression coverage for Track’s detailed public Upcoming Events feed."""

from datetime import date

import track_calendar


def test_eclipse_event_has_required_detail() -> None:
    eclipse = next(
        event
        for event in track_calendar.NOTABLE_ASTRONOMICAL_EVENTS
        if event["kind"] == "lunar_eclipse"
    )
    assert eclipse["date"] == "2026-08-28"
    assert eclipse["date_label"] == "Aug 27–28"
    assert "Partial Lunar Eclipse" in eclipse["title"]
    assert "Full Moon" in eclipse["title"]
    assert "BLOOD MOON" in eclipse["eyebrow"]
    assert "96.3%" in eclipse["detail"]
    assert "10:34 p.m. EDT" in eclipse["timing"]
    assert "12:13 a.m. EDT" in eclipse["timing"]


def test_upcoming_feed_merges_notable_and_lunar_events() -> None:
    events = track_calendar._upcoming_event_feed(date(2026, 8, 27))
    assert events == sorted(events, key=lambda event: (event["date"], event["title"]))
    assert any(event["kind"] == "lunar_eclipse" for event in events)
    assert any(event["kind"] == "lunar_phase" for event in events)
    assert any(event["title"] == "New Moon" for event in events)
    assert any(event["title"] == "Orionids Meteor Shower Peak" for event in events)
    assert any(event["title"] == "Geminids Meteor Shower Peak" for event in events)
    assert not any(
        event["title"] == "Full Moon" and event["date"] == "2026-08-28"
        for event in events
    ), "The eclipse card already gives the coincident Full Moon its dedicated detail."


def test_calendar_source_renders_feed_below_calendar() -> None:
    source = open("track_calendar.py", encoding="utf-8").read()
    assert "track-upcoming-title" in source
    assert "✦ Upcoming Events:" in source
    assert "track-upcoming-card" in source
    assert "_render_upcoming_events(today)" in source
    assert "Daily moon phases, notable skywatching events, and your private calendar." not in source
    assert 'st.popover("✎ Private event"' in source
    assert "track-calendar-footer" in source
    assert "track-private-event-control" in source
    assert "with st.expander(f\"✎ Add a private note" not in source
    assert source.index("track-legend") < source.rindex("_render_upcoming_events(today)")


if __name__ == "__main__":
    test_eclipse_event_has_required_detail()
    test_upcoming_feed_merges_notable_and_lunar_events()
    test_calendar_source_renders_feed_below_calendar()
    print("Track Upcoming Events checks passed.")
