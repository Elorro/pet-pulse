-- Baseline for tables that were created outside supabase/migrations (posts by the
-- retired Alembic setup, the rest in the Supabase dashboard). This matches the
-- production schema as of 2026-10-20 and is already applied there; mark it with
-- `supabase migration repair --status applied 20261020190000` instead of running it.

create table if not exists public.posts (
    id uuid not null primary key,
    author_id uuid not null references public.users (id),
    content varchar(5000) not null,
    created_at timestamptz not null,
    media_url text
);
alter table public.posts enable row level security;

create table if not exists public."like" (
    id uuid not null default gen_random_uuid() primary key,
    created_at timestamptz not null default now(),
    post_id uuid references public.posts (id) on update cascade on delete cascade,
    user_id uuid references public.users (id) on update cascade on delete cascade
);
alter table public."like" enable row level security;

-- Unused by the API: "like" already records the post. Kept because it exists in
-- production; drop it in a later migration once nobody needs it.
create table if not exists public.post_likes (
    id uuid not null default gen_random_uuid() primary key,
    created_at timestamptz not null default now(),
    post_id uuid references public.posts (id) on update cascade on delete cascade,
    like_id uuid references public."like" (id) on update cascade on delete cascade
);
alter table public.post_likes enable row level security;

create table if not exists public.coment (
    id uuid not null default gen_random_uuid() primary key,
    created_at timestamptz not null default now(),
    post_id uuid references public.posts (id) on update cascade on delete cascade,
    text text,
    media text,
    user_id uuid not null references public.users (id) on update cascade on delete cascade
);
alter table public.coment enable row level security;
