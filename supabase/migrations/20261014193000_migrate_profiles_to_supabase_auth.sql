-- Keep the existing public.users records and posts intact while Supabase Auth
-- becomes the source of truth for new identities and passwords.
-- NOT VALID preserves legacy rows that have not yet been imported into Auth,
-- while enforcing the relationship for every new profile row.
alter table public.users
    alter column hashed_password drop not null;

alter table public.users
    add constraint users_auth_user_id_fkey
    foreign key (id) references auth.users (id) on delete cascade
    not valid;

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.users (
        id,
        username,
        full_name,
        email,
        photo_url,
        created_at
    )
    values (
        new.id,
        coalesce(
            nullif(new.raw_user_meta_data ->> 'username', ''),
            'user_' || left(replace(new.id::text, '-', ''), 12)
        ),
        new.raw_user_meta_data ->> 'full_name',
        new.email,
        nullif(new.raw_user_meta_data ->> 'photo_url', ''),
        coalesce(new.created_at, now())
    );
    return new;
end;
$$;

drop trigger if exists on_auth_user_created_profile on auth.users;

create trigger on_auth_user_created_profile
    after insert on auth.users
    for each row execute procedure public.handle_new_auth_user();
