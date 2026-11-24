-- Seguimientos unilaterales. La tabla aún no existe en el proyecto remoto;
-- esta migración registra el esquema solicitado sin aplicarlo remotamente.
create table if not exists public.follows (
    follower_id uuid not null references public.users (id) on delete cascade,
    following_id uuid not null references public.users (id) on delete cascade,
    created_at timestamptz not null default now(),
    constraint follows_not_self check (follower_id <> following_id),
    constraint follows_follower_following_key unique (follower_id, following_id)
);

create index if not exists follows_following_id_idx
    on public.follows (following_id);

alter table public.follows enable row level security;

-- Los usuarios autenticados solo pueden leer relaciones donde participan.
-- Solo pueden crear y eliminar filas cuya identidad de origen sea auth.uid().
drop policy if exists follows_select_authenticated on public.follows;
create policy follows_select_authenticated on public.follows
    for select to authenticated
    using (follower_id = (select auth.uid()) or following_id = (select auth.uid()));

drop policy if exists follows_insert_own on public.follows;
create policy follows_insert_own on public.follows
    for insert to authenticated
    with check (follower_id = (select auth.uid()));

drop policy if exists follows_delete_own on public.follows;
create policy follows_delete_own on public.follows
    for delete to authenticated
    using (follower_id = (select auth.uid()));

grant select, insert, delete on public.follows to authenticated;
revoke all on public.follows from anon;
