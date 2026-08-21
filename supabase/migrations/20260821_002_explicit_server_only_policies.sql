-- LunaTicK Phase B follow-on: explicit server-only RLS policies.
--
-- The first migration revoked anon/authenticated table privileges and enabled RLS.
-- These explicit false policies document the deny-by-default browser boundary,
-- satisfy the platform linter, and leave service_role server access unchanged.

begin;

create policy server_only_profiles on public.profiles
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_journal_entries on public.journal_entries
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_boards on public.boards
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_board_posts on public.board_posts
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_chat_messages on public.chat_messages
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_lunatick_talk_posts on public.lunatick_talk_posts
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_lunatick_talk_comments on public.lunatick_talk_comments
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_user_votes on public.user_votes
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_card_trades on public.card_trades
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_migration_log on public.migration_log
    for all to anon, authenticated
    using (false)
    with check (false);

commit;
