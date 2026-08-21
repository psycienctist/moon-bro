-- LunaTicK Phase B follow-on: foreign-key covering indexes.
-- Added in response to the Supabase performance advisor. Existing required indexes
-- are retained; this migration covers remaining profile and post foreign keys.

begin;

create index idx_board_posts_profile_auth_subject
    on public.board_posts (profile_auth_subject);

create index idx_chat_messages_profile_auth_subject
    on public.chat_messages (profile_auth_subject);

create index idx_talk_posts_profile_auth_subject
    on public.lunatick_talk_posts (profile_auth_subject);

create index idx_talk_comments_profile_auth_subject
    on public.lunatick_talk_comments (profile_auth_subject);

create index idx_user_votes_post_id
    on public.user_votes (post_id);

commit;
