-- LunaTicK Phase G follow-on: cover moderation foreign keys flagged by the performance advisor.

begin;

create index idx_moderator_roles_granted_by
    on public.moderator_roles (granted_by_auth_subject);

create index idx_moderation_actions_target_auth_subject
    on public.moderation_actions (target_auth_subject);

commit;
