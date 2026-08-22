-- LunaTicK Phase G follow-on: explicit server-only RLS policies for moderation tables.

begin;

create policy server_only_moderator_roles on public.moderator_roles
    for all to anon, authenticated
    using (false)
    with check (false);

create policy server_only_moderation_actions on public.moderation_actions
    for all to anon, authenticated
    using (false)
    with check (false);

commit;
