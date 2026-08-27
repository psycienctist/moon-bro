-- Reddit-style voting for the active LunaTicK Talk message board.
-- Vote records are kept server-only and are separate from retired LunaTicK Talk votes.

alter table public.board_posts
    add column if not exists upvotes integer not null default 0 check (upvotes >= 0),
    add column if not exists downvotes integer not null default 0 check (downvotes >= 0);

create table if not exists public.board_post_votes (
    profile_auth_subject text not null references public.profiles(auth_subject) on delete cascade,
    board_post_id bigint not null references public.board_posts(id) on delete cascade,
    vote_type text not null check (vote_type in ('up', 'down')),
    created_at timestamptz not null default timezone('utc', now()),
    primary key (profile_auth_subject, board_post_id)
);

create index if not exists idx_board_post_votes_post_id
    on public.board_post_votes (board_post_id);

alter table public.board_post_votes enable row level security;

revoke all on table public.board_post_votes from anon, authenticated;
grant select, insert, update, delete on table public.board_post_votes to service_role;

create policy server_only_board_post_votes on public.board_post_votes
    for all
    to service_role
    using (true)
    with check (true);
