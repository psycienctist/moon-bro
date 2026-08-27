from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
feature_source = Path("reading_requests.py").read_text(encoding="utf-8")
store_source = Path("supabase_store.py").read_text(encoding="utf-8")
migration_source = Path("supabase/migrations/20260827_014_reading_requests_private_messages.sql").read_text(encoding="utf-8")

assert 'import reading_requests' in app_source
assert 'READING_REQUESTS_MODULE_VERSION' in app_source
assert 'reading_requests.init_reading_requests_db()' in app_source
assert 'elif current_page == "Reading Requests":' in app_source
assert '✦ Reading Requests' in app_source
assert 'current[\'moon_vibe\']' not in app_source
assert 'st-key-home-reading-entry' in app_source
assert 'min-height: 2.1rem' in app_source

assert 'MESSAGE_REFRESH_SECONDS = 5' in feature_source
assert 'def save_reader_profile' in feature_source
assert 'def create_request' in feature_source
assert 'def accept_request' in feature_source
assert 'def list_messages' in feature_source
assert 'def send_message' in feature_source
assert 'Only you and the matched reader/requester' in feature_source
assert 'if not request or not _is_participant(request):' in feature_source

assert 'def upsert_reading_reader' in store_source
assert 'def create_reading_request' in store_source
assert 'def create_reading_message' in store_source
assert 'def close_reading_request' in store_source

assert 'create table if not exists public.reading_readers' in migration_source
assert 'create table if not exists public.reading_requests' in migration_source
assert 'create table if not exists public.reading_messages' in migration_source
assert 'enable row level security' in migration_source
assert 'revoke all on table public.reading_readers, public.reading_requests, public.reading_messages' in migration_source
print("Reading Requests compact-home and privacy checks passed.")
