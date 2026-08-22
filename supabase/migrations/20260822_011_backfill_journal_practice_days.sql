-- Backfill owner-only practice dates from existing private journal timestamps.
-- This copies no journal content, prompt text, or chart data.

insert into public.journal_practice_days (profile_auth_subject, practice_date)
select
    profile_auth_subject,
    (created_at at time zone 'UTC')::date as practice_date
from public.journal_entries
on conflict (profile_auth_subject, practice_date) do nothing;
