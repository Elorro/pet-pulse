-- The API currently owns authentication and stores accounts in public.users.
-- Keep the profile fields on that existing table to avoid duplicating username
-- and email in a second table.
create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    username varchar(50) not null unique,
    full_name varchar(120),
    email varchar(255) not null unique,
    photo_url varchar(2048),
    hashed_password varchar(255) not null,
    created_at timestamptz not null default now()
);

-- The API may have created public.users before migrations were introduced.
alter table public.users
    add column if not exists full_name varchar(120),
    add column if not exists photo_url varchar(2048);

-- The table contains password hashes and should not be directly exposed through
-- Supabase's Data API. The backend connects to Postgres directly.
alter table public.users enable row level security;
