"""Static safety and layout checks for the Track calendar redesign."""

from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
track_source = Path("track_calendar.py").read_text(encoding="utf-8")
store_source = Path("supabase_store.py").read_text(encoding="utf-8")
migration_source = Path("supabase/migrations/20260822_009_private_calendar_entries.sql").read_text(encoding="utf-8")
backup_source = Path("supabase_backup.py").read_text(encoding="utf-8")

assert "track_calendar.render_track_tab()" in app_source
assert 'if str(st.query_params.get("track_day", "")).strip():' in app_source
assert 'st.session_state.nav_page = "Calendar"' in app_source
assert 'if page_name != "Calendar":\n        st.query_params.pop("track_day", None)' in app_source
assert "html, body, .stApp" in app_source
assert "overflow-x: hidden;" in app_source
assert ".stApp::after" in app_source
assert 'mobile_grid_private_entries_v2' in app_source
assert "header_cols = st.columns(7)" not in app_source
assert 'TRACK_MODULE_VERSION = "mobile_grid_private_entries_v2"' in track_source
assert "grid-template-columns:repeat(7,minmax(0,1fr))" in track_source
assert "aspect-ratio:1/1" in track_source
assert "Total Lunar Eclipse" in track_source
assert "Partial Lunar Eclipse" in track_source
assert "Add to device calendar" in track_source
assert "track-event-strip" in track_source
assert 'st.container(key="track-month-nav")' in track_source
assert '.st-key-track-month-nav [data-testid="stHorizontalBlock"]' in track_source
assert "upcoming_events = sorted(" in track_source
assert "if event_day >= today" in track_source
assert "Add a private note" in track_source
assert "BEGIN:VALARM" in track_source
assert "entry_date" in track_source
assert "cycle_marker" in track_source
assert '"started", "ended"' in track_source
assert "Only you can see these notes and observed cycle markers." in track_source
assert "public_profile" not in track_source
assert "calendar_entries" in store_source
assert "profile_auth_subject" in store_source
assert "calendar_entries" in backup_source
assert "enable row level security" in migration_source
assert "revoke all on table public.calendar_entries from anon, authenticated" in migration_source
assert "server_only_calendar_entries" in migration_source
assert "cycle_marker in ('started', 'ended')" in migration_source
assert "severity between 1 and 5" in migration_source

print("Track calendar mobile-grid, event, reminder, and private-entry guards passed.")
