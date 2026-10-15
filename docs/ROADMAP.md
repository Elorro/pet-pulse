# Roadmap

What to build next across the backend (`pet-pulse`) and the web app
(`pet-pulse-web`), in order. Update this file as items land.

Last updated: 2026-10-15

---

## Where things stand

**Backend (`pet-pulse`)**

- Supabase Auth is integrated. Protected routes verify the Supabase JWT
  locally against the project's JWKS.
- `GET /api/v1/auth/me` returns the caller's profile and creates the local
  `users` row on first call.
- `GET /api/v1/posts/` lists posts with `limit`/`offset`.
- `POST /api/v1/posts/` creates a post for the signed-in user.
- `POST /api/v1/auth/signup`, `/login`, `/refresh`, `/logout` wrap the
  Supabase SDK.

**Web (`pet-pulse-web`)**

- Next.js app with sign up, sign in, auth callback, sign out, and a protected
  `/feed` route.
- Typed FastAPI client generated from the OpenAPI schema.
- The feed page calls `/auth/me` and shows the username. Posts are not
  rendered yet.

---

## Open decision: the FastAPI auth endpoints

The web app signs users in **directly with Supabase** from the browser
(`supabase-js` + `@supabase/ssr`), not through the FastAPI `/auth/signup`,
`/login`, `/refresh`, or `/logout` endpoints. That is the right call for
Next.js: the SSR library manages session cookies and token refresh.

It does mean those four endpoints are unused. Options:

- **Keep them** for a future Flutter client that should not embed the
  Supabase SDK.
- **Delete them** so there is one auth path to maintain.

`GET /auth/me` and JWT verification stay either way. Decide before the
endpoints drift from what the web app actually does.

---

## Next steps

### 1. Make posts feed-ready (backend)

The list endpoint returns only `author_id`, so the feed cannot show who
posted.

- [ ] Include the author's `username` in each post (join `users`).
- [ ] `GET /api/v1/posts/{id}` for a single post.
- [ ] `DELETE /api/v1/posts/{id}`, author only. Return 404 for other users'
      posts rather than 403, so post existence is not leaked.
- [ ] Replace `offset` with cursor pagination (`before=<created_at>` or an
      opaque cursor). Offset skips or repeats posts as new ones arrive.
- [ ] Tests for each of the above.

Small, and it unblocks the frontend.

### 2. Feed and composer (web)

- [ ] Regenerate API types (`pnpm gen:api`) after step 1.
- [ ] Replace "Posts will appear here" with the post list from the API.
- [ ] Composer form that calls `POST /api/v1/posts/`.
- [ ] Load more on scroll or button, using the cursor from step 1.
- [ ] Delete button on the user's own posts.

### 3. Photo uploads (both)

Posts without pictures will feel empty in a pet app.

- [ ] Create a private `pet-photos` Supabase Storage bucket with a policy that
      lets users write only to their own folder (`<user_id>/...`).
- [ ] Web uploads the image directly to Storage, then sends the object path
      with the post.
- [ ] Backend adds an optional `image_path` to posts, validates it starts
      with the caller's user ID, and returns a signed URL when listing.

The bucket and policy should be the first real migration (see setup debt
below).

### 4. Comments and reactions (both)

- [ ] `comments` table and model. The `Comment` domain entity already exists
      with no table or endpoints.
- [ ] `GET` and `POST /api/v1/posts/{id}/comments`.
- [ ] Reactions: one per user per post, with a unique constraint.
- [ ] Comment counts and reaction counts on the feed.

---

## Setup debt to fix along the way

- [ ] **Migrations.** Tables are created by `Base.metadata.create_all` on app
      startup and there is no migrations folder. That breaks the first time a
      column changes. Set up Supabase CLI migrations (`supabase init`,
      `supabase migration new`) **before step 3**, and remove `create_all`
      from startup.
- [ ] **CORS.** Origins are hardcoded to localhost in `app/main.py`, which
      will block the deployed web app. Move them into `Settings` as
      `CORS_ORIGINS`.
- [ ] **Unused auth endpoints.** Resolve the decision above.

---

## Later

- Lost-pet and adoption reports (README phase 2).
- On-device pet recognition with pgvector matching (README phase 3, see
  `README_AI_EDGE.md`).
- Flutter mobile client.
