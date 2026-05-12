# Copilot Instructions

## Build, test, and lint commands

```bash
# Full local stack when work depends on Postgres, Neo4j, Redis, Telegram, or the web UI
docker-compose up -d

# Next.js frontend
npm run build
npm run lint
npm run lint -- --file src/app/login/page.tsx

# Python test suite
pytest tests/
pytest tests/test_skill_manager.py -q
pytest tests/test_skill_manager.py -k discovery_and_injection -q

# Python formatting / linting referenced by the repo docs
black .
flake8 .
flake8 api/auth.py
```

## High-level architecture

- `docker-compose.yml` is the best high-level map of the runtime system: `core` (FastAPI API), `frontend` (Next.js), `telegram_client` (Telegram bot + internal FastAPI service), `telegram_panel` (Telegram WebApp bridge), `db` (Postgres + pgvector), `neo4j`, `redis`, and `kokoro-tts`.
- `run_api.py` starts the central FastAPI app in `api/main.py`. Startup initializes SQLAlchemy tables, LLMs, embeddings, Whisper, WebSocket infrastructure, and scheduled tools before serving requests.
- The API layer lives in `api/*.py`, but most durable logic is pushed down into `core/*`, `knowledge_graph/*`, and `telegram_client/*`. Read routers together with the manager they call before changing behavior.
- The user model is intentionally platform-agnostic. `core/database.py` centers everything on `Account` plus `PlatformIdentity`, so web login, Telegram login, notes, chats, workspaces, reminders, and analysis all converge on `account_id`.
- The knowledge system is hybrid, not graph-only or vector-only. `core/memory_manager.py` handles chunking and pgvector-backed semantic retrieval in Postgres, while `knowledge_graph/graph_integration.py` and related modules push conceptual relationships into Neo4j and emit graph progress over WebSockets.
- The Next.js app uses the App Router under `src/app`. Root layout wires auth, theme, and user settings providers; the dashboard layout adds workspace, WebSocket, task, DnD, and proactive insight providers around the main app shell.
- `src/lib/api.ts` is the frontend API entrypoint. It injects the JWT from `localStorage`, centralizes 401/422 handling, and is the default client for UI data fetching.
- The Telegram surfaces are separate from the Next.js frontend. `run_telegram_bot.py` runs the Telegram bot lifecycle and handlers, while `run_telegram_panel.py` validates Telegram WebApp init data and proxies authenticated requests into the central API.

## Key conventions

- Treat `core.config.settings` as the canonical configuration source. It loads environment variables early, resolves Docker secrets through `utils.docker_secrets.get_secret`, and switches some defaults for in-container service-to-service URLs.
- Preserve the account/workspace model. Prefer `account_id` for user-scoped data and pass `workspace_id` explicitly for workspace-scoped features; do not reintroduce platform-specific IDs into core domain logic.
- In API routers, use injected async sessions (`Depends(get_db_session)`). In lower-level helpers and managers, the common pattern is `async with DBSession(SessionLocal)` so commit/rollback is handled consistently.
- Keep frontend data access inside the shared axios client in `src/lib/api.ts` unless a file already has a strong reason not to. Auth depends on the `authToken` localStorage key, and workspace selection depends on `currentWorkspaceId`.
- Follow the existing App Router structure and `@/*` import alias from `tsconfig.json`. Many dashboard pages are client components and rely on context providers already mounted in `src/app/layout.tsx` and `src/app/(dashboard)/layout.tsx`.
- Reuse the skill-loading pattern instead of hardcoding tool descriptions. `tests/test_skill_manager.py` shows that a skill can ship as `skills/<name>.py` plus `skills/<name>.md`, and the Markdown file overrides the Python description shown to the agent.
- Expect Spanish user-facing copy, logs, and comments in much of the backend and UI. Match the surrounding file’s language rather than normalizing everything to English.
- When touching agent behavior, remember the agent is not a thin LangChain wrapper. `core/agent.py` explicitly composes memory, prompt context, tool selection, and session identifiers; changes there usually affect chat, tools, and retrieval together.
