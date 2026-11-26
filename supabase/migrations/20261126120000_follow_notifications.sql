-- Follow notifications have no associated post. Existing like/comment rows keep
-- their post references and source columns unchanged.
alter table public.notifications
    alter column post_id drop not null;

