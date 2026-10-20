-- A like always belongs to one post and one user, and a user can like a post
-- only once. The API relies on this constraint to ignore duplicate likes.
alter table public."like"
    alter column post_id set not null,
    alter column user_id set not null,
    add constraint like_post_id_user_id_key unique (post_id, user_id);
