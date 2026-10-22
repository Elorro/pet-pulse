-- The deployed Supabase table is named `comment`. Older baseline snapshots
-- used `coment`, so rename it only in environments that still have that name.
do $$
begin
    if to_regclass('public."comment"') is not null
       and to_regclass('public.coment') is not null then
        raise exception 'Both public.comment and public.coment exist; resolve the duplicate tables before continuing';
    elsif to_regclass('public."comment"') is null
       and to_regclass('public.coment') is not null then
        alter table public.coment rename to "comment";
    elsif to_regclass('public."comment"') is null then
        raise exception 'Neither public.comment nor public.coment exists';
    end if;
end
$$;
