"""Static privacy and integration guards for the no-API Daily Reflection system."""

from pathlib import Path

reflection_source = Path("daily_reflection.py").read_text(encoding="utf-8")
journal_source = Path("journal.py").read_text(encoding="utf-8")
store_source = Path("supabase_store.py").read_text(encoding="utf-8")
backup_source = Path("supabase_backup.py").read_text(encoding="utf-8")
migration_source = Path("supabase/migrations/20260822_010_private_journal_practice_days.sql").read_text(encoding="utf-8")
backfill_source = Path("supabase/migrations/20260822_011_backfill_journal_practice_days.sql").read_text(encoding="utf-8")
policy_source = Path("supabase/migrations/20260822_012_journal_practice_server_only_policy.sql").read_text(encoding="utf-8")

for badge in ("Mooned", "Moon Lit", "Moonwalker", "Over the Moon"):
    assert badge in reflection_source
assert "LunaTick Talker" not in reflection_source
assert "talk_db" not in reflection_source
assert "get_recent_entries" not in reflection_source
assert "DeepSeek" not in reflection_source
assert "openai" not in reflection_source.lower()
assert "journal_practice_days" in reflection_source
assert "record_practice_day" in reflection_source
assert "record_journal_practice_day" in store_source
assert "list_journal_practice_days" in store_source
assert '"journal_practice_days"' in store_source
assert '"journal_practice_days"' in backup_source
assert "enable row level security" in migration_source
assert "revoke all on table public.journal_practice_days from anon, authenticated" in migration_source
assert "No journal content is stored here" in migration_source
assert "create policy server_only_journal_practice_days" in migration_source
assert "create policy server_only_journal_practice_days" in policy_source
assert "using (false)" in policy_source
assert "with check (false)" in policy_source
assert "from public.journal_entries" in backfill_source
assert "on conflict (profile_auth_subject, practice_date) do nothing" in backfill_source
assert "reflection_ui.record_practice_day()" in journal_source
assert "daily_reflection_write_intent" in journal_source

print("Daily Reflection no-API, owner-only practice, and badge guards passed.")
