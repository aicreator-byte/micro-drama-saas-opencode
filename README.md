# Micro Drama SaaS — OpenCode leg

Micro-drama production workspace: write a Series Bible, build characters,
locations and episodes, generate video prompts, and run Google Flow tasks —
manually or fully AI-generated from a title alone.

**Status (Nov 2026):** the full loop works end to end with a real LLM
(NVIDIA NIM). **Auto-Generate** (title → bible, characters, locations,
episodes, video prompts) runs as an async background job with live
per-step progress. Google Accounts support encrypted login + automatic
fallback between accounts, and Flow Bridge automation runs in the browser
via Playwright. **Video itself is still generated manually in Google Flow:**
this app writes the prompts and tracks readiness, it never renders video.

## Quick Start (Development)

### Prerequisites
- Node.js 20+ (frontend), Python 3.12+ (backend)
- Docker & Docker Compose (optional; for Postgres/Redis)
- An NVIDIA API key (`NVIDIA_API_KEY`) for real LLM generation
  (without it the backend still runs, but AI calls fail)

### Backend (this leg runs on port 8002)

```bash
cd opencode

# 1. Copy the environment file and fill in your keys.
cp .env.example .env
# Edit .env: SECRET_KEY, ENCRYPTION_KEY, NVIDIA_API_KEY, ...
# NEVER commit .env — it is git-ignored. Only .env.example belongs in git.

# 2. Start the server (pins PYTHONPATH + DATABASE_URL for you).
./start-backend.sh
# Backend API: http://127.0.0.1:8002
# API docs:    http://127.0.0.1:8002/docs
```

Notes:
- `./start-backend.sh` defaults to a local sqlite DB
  (`micro_drama_smoke.db` in this directory) and enables Flow automation.
  Override with env vars: `PORT=8002 DATABASE_URL=sqlite+aiosqlite:///./micro_drama.db
  FLOW_AUTOMATION_ENABLED=0 ./start-backend.sh`.
- The app reads `.env` from the leg root / backend directory, never from
  the process working directory — you can start it from anywhere and the
  key is still found. If the configured `DATABASE_URL` needs a driver that
  is not installed (e.g. `postgresql+asyncpg` without asyncpg), the app
  logs a warning and falls back to local sqlite instead of crashing.
- `ENCRYPTION_KEY` must be set in `.env`: if it is missing a random key is
  generated per process, and Google account passwords encrypted earlier
  become undecryptable after a restart.

### Frontend

```bash
cd app/frontend
npm install

# Point the frontend at this leg's backend, then build + start:
NEXT_PUBLIC_API_URL=http://localhost:8002/api/v1 npm run build
NEXT_PUBLIC_API_URL=http://localhost:8002/api/v1 npm start
# Frontend: http://localhost:3000
```

(For dev: `npm run dev` with the same `NEXT_PUBLIC_API_URL`.)

### Docker Compose (alternative)

```bash
docker-compose up -d
# Frontend: http://localhost:3000, Backend API: http://localhost:8000
```

## Auto-Generate (title → full project)

One POST creates a job with 5 sequential steps and runs it **in the
background** — the request returns `201` immediately with status `running`,
and `GET` polls the live per-step status:

1. **Series Bible** — premise, plot, subplots, world, tone. When no genre
   is given, the LLM infers it from the title (no silent default).
2. **Characters** — the cast is invented by the LLM (minimum 4 usable
   characters, spec §9.1 — the step fails below that).
3. **Locations** — world building (minimum 3 usable locations).
4. **Episodes** — outline + episode rows (existing numbers are skipped).
5. **Prompts** — one video-generation prompt per episode, generated in
   chunks of 5 episodes per LLM call; the step fails unless **every**
   episode is covered (no partial insert).

Each step writes straight into the project tables (no manual Apply).
A failed step stops the job; `POST .../retry/{step}` re-runs that step
and continues. Re-running never duplicates rows. The job input lives on
the job itself — it never rewrites the project title/genre.

- `POST /api/v1/projects/{id}/auto-generate` — create a job (201, running)
- `GET /api/v1/projects/{id}/auto-generate/{job_id}` — poll job + steps
- `POST /api/v1/projects/{id}/auto-generate/{job_id}/retry/{step}` — retry a failed step

## Project Structure

```
opencode/
├── start-backend.sh      # start the backend (port 8002) with pinned env
├── app/
│   ├── backend/          # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/v1/   # API routes (incl. auto_generate, story/scene
│   │   │   │             #   engine, flow_bridge, google_accounts)
│   │   │   ├── core/     # Config, security, database
│   │   │   ├── models/   # SQLAlchemy models
│   │   │   ├── schemas/  # Pydantic schemas
│   │   │   ├── services/ # ai_client (NVIDIA NIM + mock provider), browser
│   │   │   └── main.py   # FastAPI app
│   │   ├── alembic/      # Database migrations (001_initial.py is the base)
│   │   ├── tests/        # pytest (187 passed, Nov 2026)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/         # Next.js frontend
│       ├── src/
│       │   ├── app/      # App Router pages (incl. projects/[id])
│       │   ├── lib/      # API client, stores
│       │   └── types/
│       ├── package.json
│       └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/change-password` - Change password
- `POST /api/v1/auth/logout` - Logout

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `PATCH /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Auto-Generate
- `POST /api/v1/projects/{id}/auto-generate` - Create a job (async, 201)
- `GET /api/v1/projects/{id}/auto-generate/{job_id}` - Poll job + per-step status
- `POST /api/v1/projects/{id}/auto-generate/{job_id}/retry/{step}` - Retry a failed step

### Series Bible
- `POST /api/v1/projects/{id}/series-bible` - Create series bible
- `GET /api/v1/projects/{id}/series-bible` - Get series bible
- `PATCH /api/v1/projects/{id}/series-bible` - Update series bible
- `DELETE /api/v1/projects/{id}/series-bible` - Delete series bible

### Characters
- `POST /api/v1/projects/{id}/characters` - Create character
- `GET /api/v1/projects/{id}/characters` - List characters
- `GET /api/v1/projects/{id}/characters/{char_id}` - Get character
- `PATCH /api/v1/projects/{id}/characters/{char_id}` - Update character
- `DELETE /api/v1/projects/{id}/characters/{char_id}` - Delete character

### Locations
- `POST /api/v1/projects/{id}/locations` - Create location
- `GET /api/v1/projects/{id}/locations` - List locations
- `GET /api/v1/projects/{id}/locations/{loc_id}` - Get location
- `PATCH /api/v1/projects/{id}/locations/{loc_id}` - Update location
- `DELETE /api/v1/projects/{id}/locations/{loc_id}` - Delete location

### Episodes, Scenes, Shots
- `POST /api/v1/projects/{id}/episodes` - Create episode
- `GET /api/v1/projects/{id}/episodes` - List episodes
- `GET /api/v1/projects/{id}/episodes/{ep_id}` - Get episode
- `PATCH /api/v1/projects/{id}/episodes/{ep_id}` - Update episode
- `DELETE /api/v1/projects/{id}/episodes/{ep_id}` - Delete episode
- `POST /api/v1/projects/{id}/episodes/{ep_id}/scenes` - Create scene
- `GET /api/v1/projects/{id}/episodes/{ep_id}/scenes` - List scenes
- `POST /api/v1/projects/{id}/episodes/{ep_id}/scenes/{sc_id}/shots` - Create shot

### Episode Revisions (snapshots, immutable — no update endpoint)
- `POST /api/v1/projects/{id}/episodes/{ep_id}/revisions` - Snapshot the episode now
- `GET /api/v1/projects/{id}/episodes/{ep_id}/revisions` - List revisions
- `GET /api/v1/projects/{id}/episodes/{ep_id}/revisions/{rev_id}` - Get one revision
- `DELETE /api/v1/projects/{id}/episodes/{ep_id}/revisions/{rev_id}` - Delete a revision

### Dialogues
- `POST /api/v1/projects/{id}/episodes/{ep_id}/scenes/{sc_id}/dialogues` - Create dialogue line
- `GET /api/v1/projects/{id}/episodes/{ep_id}/scenes/{sc_id}/dialogues` - List dialogue lines
- `GET /api/v1/projects/{id}/episodes/{ep_id}/scenes/{sc_id}/dialogues/{id}` - Get one line
- `PATCH /api/v1/projects/{id}/episodes/{ep_id}/scenes/{sc_id}/dialogues/{id}` - Update a line
- `DELETE /api/v1/projects/{id}/episodes/{ep_id}/scenes/{sc_id}/dialogues/{id}` - Delete a line

### Prompts (video/image generation prompts)
- `POST /api/v1/projects/{id}/prompts` - Create prompt
- `GET /api/v1/projects/{id}/prompts` - List prompts
- `GET /api/v1/projects/{id}/prompts/{prompt_id}` - Get prompt
- `PATCH /api/v1/projects/{id}/prompts/{prompt_id}` - Update prompt
- `DELETE /api/v1/projects/{id}/prompts/{prompt_id}` - Delete prompt
- `POST /api/v1/projects/{id}/prompts/{prompt_id}/use` - Mark a prompt used

### Story Engine / Scene Engine
- `POST /api/v1/projects/{id}/story-engine/tasks` - Create story task
- `POST /api/v1/projects/{id}/story-engine/tasks/{id}/execute` - Run it (LLM)
- `POST /api/v1/projects/{id}/story-engine/tasks/{id}/apply` - Apply its output
- Same shape under `/scene-engine/tasks` for scene breakdowns, shots, dialogue.

### Google Accounts (max 20 per user)
- `POST /api/v1/google-accounts` - Add account (email + password, stored encrypted)
- `GET /api/v1/google-accounts` - List accounts
- `GET /api/v1/google-accounts/{id}` - Get account
- `PATCH /api/v1/google-accounts/{id}` - Update account
- `GET /api/v1/google-accounts/oauth/authorize` - Get the Google OAuth URL
- `GET /api/v1/google-accounts/oauth/callback` - OAuth callback
- `POST /api/v1/google-accounts/{id}/verify` - Verify account
- `POST /api/v1/google-accounts/{id}/refresh` - Refresh session
- `DELETE /api/v1/google-accounts/{id}` - Disconnect account

Accounts log in through a real browser (Playwright, persistent profile per
account). When an account fails (bad password, expired session, challenge,
quota), the next account is tried automatically and the attempt history is
kept (`fallback_history`).

### Flow Bridge
- `POST /api/v1/projects/{id}/tasks` - Create task
- `GET /api/v1/projects/{id}/tasks` - List tasks
- `GET /api/v1/projects/{id}/tasks/{task_id}` - Get task
- `PATCH /api/v1/projects/{id}/tasks/{task_id}` - Update task
- `DELETE /api/v1/projects/{id}/tasks/{task_id}` - Delete task
- `POST /api/v1/projects/{id}/tasks/{task_id}/execute` - Execute a task
  (validates the account + marks the task ready for generation — video
  itself is still produced manually in Google Flow)
- `POST /api/v1/projects/{id}/tasks/{task_id}/execute-browser` - Execute in the browser
- `POST /api/v1/projects/{id}/tasks/{task_id}/retry` - Retry a task
- `POST /api/v1/projects/{id}/tasks/{task_id}/assets` - Create asset
- `GET /api/v1/projects/{id}/tasks/{task_id}/assets` - List task assets
- `GET /api/v1/projects/{id}/assets` - List project assets

### Audit Logs (superuser only)
- `GET /api/v1/audit-logs` - List audit logs
- `GET /api/v1/audit-logs/{id}` - Get audit log

## Multi-Tenant Security

The application implements strict multi-tenant isolation:

1. **Project Ownership** - Every project belongs to a user (owner_id)
2. **Access Control** - All API routes verify project ownership before operations
3. **Data Isolation** - Users can only access their own projects, characters, locations, etc.
4. **Google Account Isolation** - Each user's Google accounts are isolated
5. **Audit Logging** - All sensitive operations are logged

**Secrets:** `.env` is git-ignored and must never be committed — it holds
`SECRET_KEY`, `ENCRYPTION_KEY`, `NVIDIA_API_KEY` and Google credentials.
Only `.env.example` (no real values) belongs in git. Before any push,
verify with `git status` / `git ls-files` that no `.env` is tracked.

## Testing

### Backend Tests
```bash
cd app/backend
pytest -v
# 187 passed (Nov 2026). Tests use the mock AI provider
# (AppSettings with provider "mock") — no real LLM calls, no network.
```

### Frontend
```bash
cd app/frontend
npx tsc --noEmit   # type-check
npm run build      # production build (14 routes)
```

## Known Limitations

1. **Video Generation** - No direct video rendering in this app; video is
   produced manually in Google Flow from the generated prompts.
2. **Google login is not verified end-to-end** - Browser login reaches
   Google's sign-in form from a normal network, but from this VM the
   browser path fails at egress and Google may demand verification /
   bot-detection. Captcha / 2FA need manual handling.
3. **Async jobs are not resumed after a server restart** - a job left
   `running` when the server stops stays `running`; poll it and retry its
   failed step.
4. **File Upload** - Asset upload to S3/local storage not fully implemented.
5. **Real-time Updates** - No WebSocket support for live collaboration.
6. **Payment/Billing** - Subscription management not implemented.
7. **Email Verification** - Email verification flow not implemented.

## Future Development

1. **Resume async jobs on startup** - pick up jobs left `running` by a restart.
2. **Live progress over WebSocket/SSE** - replace the 2s GET polling.
3. **Video Pipeline** - FFmpeg-based video assembly from Flow outputs.
4. **Asset Management** - S3-compatible storage with CDN.
5. **Collaboration** - Real-time editing with WebRTC/WebSockets.
6. **Billing** - Stripe integration for subscriptions.
7. **Mobile App** - React Native / Flutter frontend.
8. **Analytics** - Production metrics and cost tracking.
9. **Templates** - Genre-specific project templates.
10. **Export** - Multiple export formats (Final Draft, Fountain, etc.)

## License

MIT License - See LICENSE file for details.
