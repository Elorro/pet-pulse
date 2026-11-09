-- Schema record for public.notifications, already created manually in Supabase.
-- CREATE IF NOT EXISTS keeps this migration safe on that project and creates
-- the table only in environments that have not received the manual change.
create table if not exists public.notifications (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    read_at timestamptz,
    actor_id uuid not null references public.users (id) on delete cascade,
    recipient_id uuid not null references public.users (id) on delete cascade,
    post_id uuid not null references public.posts (id) on delete cascade,
    type text not null,
    source_like_id uuid references public."like" (id) on delete cascade,
    source_comment_id uuid references public."comment" (id) on delete cascade
);

create unique index if not exists notifications_source_like_id_key
    on public.notifications (source_like_id) where source_like_id is not null;
create unique index if not exists notifications_source_comment_id_key
    on public.notifications (source_comment_id) where source_comment_id is not null;

alter table public.notifications enable row level security;

drop policy if exists notifications_select_own on public.notifications;
create policy notifications_select_own on public.notifications
    for select to authenticated using (recipient_id = (select auth.uid()));

drop policy if exists notifications_update_own on public.notifications;
create policy notifications_update_own on public.notifications
    for update to authenticated
    using (recipient_id = (select auth.uid()))
    with check (recipient_id = (select auth.uid()));

-- The Data API may otherwise permit changing actor/post/type on an owned row.
revoke update on public.notifications from anon, authenticated;
grant update (read_at) on public.notifications to authenticated;
