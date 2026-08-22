-- Owner-only daily practice metadata for deterministic Daily Reflection streaks.
-- This table intentionally stores no journal content, prompt text, chart inputs,
-- display data, or public badges. A canonical UTC practice date is used until
-- an owner time-zone preference is explicitly designed and approved.

create table if not exists public.journal_practice_days (
    profile_auth_subject text not null
        references public.profiles(auth_subject) on delete cascade,
    practice_date date not null,
    created_at timestamptz not null default timezone('utc', now()),
    primary key (profile_auth_subject, practice_date)
);

comment on table public.journal_practice_days is
    'Owner-only daily journal practice metadata. No journal content is stored here.';
comment on column public.journal_practice_days.practice_date is
    'Canonical UTC date of a qualifying private journal entry until owner time-zone support is approved.';

alter table public.journal_practice_days enable row level security;

-- Browser roles remain deny-by-default. The server-only LunaTicK adapter owns
-- all reads and writes, matching the journal_entries privacy model.
revoke all on table public.journal_practice_days from anon, authenticated;
grant select, insert, update, delete on table public.journal_practice_days to service_role;

create policy server_only_journal_practice_days on public.journal_practice_days
    for all to anon, authenticated
    using (false)
    with check (false);
