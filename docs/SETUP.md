# Project Setup Guide

This document records the current state of the backend, the decisions made about
how PetPulse will use Supabase, and the steps to get a working development
environment. It is the checklist for bringing the repo from "skeleton" to
"runnable". Update it as steps are completed.

Last updated: 2026-10-14 (revised after PR #3)

---

## 1. Current state

The repo is a FastAPI skeleton with roughly 600 lines of Python. It does not
install, run, or pass tests yet.

**Implemented**

- FastAPI app (`app/main.py`) with CORS for localhost, security headers, and
  HTTPS redirect in production.
- Two endpoints: `POST /api/v1/auth/register` and `GET /api/v1/posts/`.
- Domain entities (`User`, `Post`, `Comment`) as dataclasses.
- Repository interfaces for users and posts, with SQLAlchemy async
  implementations.
- Dependency injection wiring a DB session into repositories.
- Settings via pydantic-settings; bcrypt helpers.

**Missing or broken**

- No ORM models. Both repositories import `app.infrastructure.db.models.*`,
  which does not exist, so the app fails at import.
- No migrations or table definitions.
- No login, no JWT issuance or verification, no protected routes.
- No endpoint to create posts.
- `register` crashes: the `User` dataclass requires `updated_at`, which the
  route never passes.
- `app/infrastructure/db/session.py` reads `DATABASE_URL` from the environment
  directly instead of using `Settings`, so the documented `.env` is ignored.
- `application/`, `dto/`, `use_cases/`, `services/`, `ml/`, `vector_store/`,
  `value_objects/`, and all test directories are empty.
- No usable lockfile. `pyproject.toml` is in Poetry format while `uv.lock` is
  an empty stub targeting Python 3.14.
- `.gitignore` only ignores aider files.
- No CI, no linter or type-checker config, no pre-commit hooks.

---

## 2. Architecture decision: how we use Supabase

Supabase provides **auth, storage, and the Postgres database**. FastAPI is the
**only API the mobile app calls for application data**.

### Auth: Supabase owns it, FastAPI fronts it

The mobile app talks **only to this API**. FastAPI exposes the auth endpoints
and calls the official Supabase SDK (`supabase-py`) behind the scenes. The
backend never stores passwords or mints tokens.

| Endpoint | Backed by |
|---|---|
| `POST /api/v1/auth/signup` | `auth.sign_up` (username stored in user metadata) |
| `POST /api/v1/auth/login` | `auth.sign_in_with_password` |
| `POST /api/v1/auth/refresh` | `auth.refresh_session` |
| `POST /api/v1/auth/logout` | Supabase logout call, revokes refresh tokens |
| `GET /api/v1/auth/me` | Local profile, created lazily on first call |

The SDK sits behind an `AuthService` port
(`app/application/interfaces/auth_service.py`) with a `SupabaseAuthService`
adapter, so routes are testable without network.

Protected routes use `get_current_user`, which verifies the Supabase JWT
locally against the project's JWKS endpoint with PyJWT (ES256/RS256, with
optional HS256 fallback for legacy projects). No network call per request.

The `users` table is a profile table keyed by the Supabase `auth.users.id`,
holding only public data (username, email, timestamps). The row is created
the first time an authenticated user calls the API.

Flutter flow: sign up or log in through this API, store the access and
refresh tokens, send `Authorization: Bearer <access_token>` on every request,
and call `/auth/refresh` on a 401.

### Storage: direct from the phone

- Pet photos for forum posts and adoption listings go to a Supabase Storage
  bucket (`pet-photos`).
- Flutter uploads directly using the user's token. A bucket policy restricts
  writes to the owner's folder.
- FastAPI never handles image bytes. Post rows store the object path only.
- The biometric flow is separate by design: the identification photo never
  leaves the device, only the embedding vector does (see `README_AI_EDGE.md`).

### Database: FastAPI connects as the backend

- SQLAlchemy async connects over the Supabase Postgres connection string using
  the service role credential. Row-Level Security is bypassed for this
  connection, so **FastAPI must enforce authorization itself** (for example,
  only the author can edit a post).
- All forum, rescue, and pgvector matching logic lives in FastAPI.

### What not to do

- Do not let Flutter talk to Supabase directly for auth or data. All auth
  goes through this API so there is one place to change providers or add
  rules. The only direct Flutter-to-Supabase call is the storage upload.

### Alternative considered

Dropping FastAPI entirely and building on Supabase's auto-generated API with
RLS and a SQL function for vector matching. Less code for a forum MVP, but the
repo is committed to a FastAPI domain layer and the matching and rescue logic
will outgrow SQL functions. Rejected for now.

---

## 3. Supabase setup

### 3.1 Create the project (browser)

1. Create a project at https://supabase.com on the free tier.
2. Pick the region closest to your users.
3. Save the database password.
4. Note the **project ref**: the 20-character ID in the dashboard URL after
   `/project/`.

### 3.2 Supabase MCP server for Claude Code (optional, recommended)

The official hosted MCP server lets Claude Code inspect the schema, read logs,
run the security and performance advisors, and read project keys.

```sh
claude mcp add --transport http supabase "https://mcp.supabase.com/mcp?project_ref=<ref>&read_only=true"
```

Then run `/mcp` inside Claude Code and complete the OAuth login.

`read_only=true` is deliberate: schema changes go in versioned migration files,
not ad-hoc MCP writes. Drop the flag only for a one-off reason.

### 3.3 Supabase CLI

```sh
brew install supabase/tap/supabase
supabase login
supabase init
supabase link --project-ref <ref>
```

This creates a `supabase/` directory with a `migrations/` folder.

### 3.4 Migrations: Supabase CLI, not Alembic

Migrations are plain SQL files under `supabase/migrations/`, applied with
`supabase db push`. This is the only migration system. Alembic is removed.

Reasons:

- Enabling `pgvector`, storage bucket policies, and the `auth.users`-linked
  `profiles` table are all SQL that Alembic cannot express naturally.
- Two migration systems against one database will drift.

SQLAlchemy stays as the query layer on top of tables the SQL migrations define.

First migration should include:

- `create extension if not exists vector;`
- `profiles` table referencing `auth.users(id)`.
- `posts` and `comments` tables.
- `pet-photos` storage bucket and owner-folder policy.

### 3.5 Local database

The Supabase CLI local stack (`supabase start`) requires Docker, which is not
installed. For now, **develop against the hosted free-tier project** and skip
Docker. Tests can use a Supabase branch or a throwaway schema. Revisit when a
second developer or CI needs an isolated database.

### 3.6 Connection notes

- Use the `postgresql+asyncpg://` scheme in the connection string.
- The free tier routes through a connection pooler. In transaction mode it does
  not support prepared statements, so either use the direct connection port or
  create the asyncpg engine with `statement_cache_size=0`.

---

## 4. Python toolchain

- System Python is 3.9; the project requires 3.11+. Homebrew has 3.14.
- **Use uv.** Neither Poetry nor uv is installed; uv is faster, simpler, and
  the stub lockfile is already uv-format.
- Rewrite `pyproject.toml` from Poetry format to standard PEP 621, then run
  `uv sync` to produce a real `uv.lock`.

### Dependency changes

Remove:

- `alembic` (replaced by Supabase CLI migrations)
- `passlib` (auth moves to Supabase)
- `psycopg2-binary` (asyncpg is the only driver)

Add:

- `pyjwt[crypto]` for verifying Supabase tokens against JWKS
- `supabase` (supabase-py) for the signup/login/refresh/logout endpoints

Keep: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`,
`sqlalchemy[asyncio]`, `asyncpg`, `pgvector`, `python-dotenv`.

Dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pre-commit`.

---

## 5. Repo hygiene

- `.gitignore`: add `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`,
  `.ruff_cache/`, `.mypy_cache/`.
- Add `ruff` and `mypy` configuration to `pyproject.toml`.
- Add `.pre-commit-config.yaml` running ruff and mypy.
- Add `.github/workflows/ci.yml` running ruff, mypy, and pytest on every PR.
- Move the hardcoded CORS origins in `app/main.py` into `Settings`.
- Trim or implement the security claims in `README.md` (rate limiting and RLS
  are promised but do not exist).

---

## 6. Environment variables

`.env.example` should become:

```
ENVIRONMENT=development

# Supabase
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<publishable/anon key from Project Settings > API Keys>
# Only for legacy projects that sign JWTs with HS256:
# SUPABASE_JWT_SECRET=
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres.<ref>:<password>@<host>:5432/postgres

# API
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

`SECRET_KEY`, `ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES` are removed; the
backend no longer issues tokens.

---

## 7. Backend work checklist

Once Supabase is created and linked:

- [ ] Rewrite `pyproject.toml` for uv; `uv sync`.
- [ ] Update `.gitignore`, add ruff/mypy config, pre-commit, CI workflow.
- [x] Update `Settings` with Supabase fields; delete JWT issuance fields. (PR #3)
- [x] Fix `session.py` to build the engine from `Settings`.
- [x] Add `app/infrastructure/db/models/` with user and post models.
- [x] Add `get_current_user` dependency verifying Supabase JWTs via JWKS. (PR #3)
- [x] Replace `auth/register` with SDK-backed signup/login/refresh/logout;
      remove `core/security.py` and `hashed_password`. (PR #3)
- [x] Add `POST /api/v1/posts/` (authenticated). (PR #3)
- [ ] Move CORS origins into `Settings`.
- [ ] Add `CommentModel` and comment endpoints.
- [ ] Write the first migration (section 3.4) and `supabase db push`.
- [ ] Add integration tests for register-free auth flow and posts CRUD.

---

## 8. Flutter

Not started. Flutter is not installed and there is no mobile directory.
Decision: keep the Flutter app in a **separate repository** so Python CI does
not trigger on Dart changes. Start once the API has endpoints worth calling.
See `README_MOBILE.md` and `README_AI_EDGE.md` for the planned on-device
inference flow.
