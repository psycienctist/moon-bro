-- Production follow-up for the practice-day table created before the explicit
-- deny-by-default policy was added to the repository migration source.

create policy server_only_journal_practice_days on public.journal_practice_days
    for all to anon, authenticated
    using (false)
    with check (false);
