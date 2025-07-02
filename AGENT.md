# AGENT.md - Kognito AI Codebase Guide

## Build/Lint/Test Commands
- **Frontend**: `npm run dev` (development), `npm run build` (production), `npm run lint` (ESLint)
- **Backend**: `python run_api.py` (FastAPI server), `python run_telegram_bot.py` (Telegram bot)
- **Docker**: `docker-compose up` (full stack), `docker-compose up core frontend` (specific services)
- **No test framework detected** - consider adding pytest for Python, Jest for TypeScript

## Architecture & Structure
- **Microservices**: FastAPI core API + Next.js frontend + Telegram bot + PostgreSQL + PGVector
- **Core modules**: `/core/` (agent, memory, database), `/api/` (REST endpoints), `/tools/` (AI tools)
- **Frontend**: Next.js 15 with TypeScript, Shadcn/ui components, Tailwind CSS
- **Database**: PostgreSQL with PGVector for embeddings, SQLAlchemy async ORM
- **AI Stack**: LangChain + Google Generative AI (Gemini) + LangGraph for agent orchestration

## Code Style Guidelines
- **Python**: Use async/await, type hints, logging, follow FastAPI patterns
- **TypeScript**: Strict mode enabled, use React hooks, functional components with memo
- **Imports**: Absolute imports with `@/` prefix for frontend, relative imports for backend
- **Naming**: snake_case (Python), camelCase (TypeScript), kebab-case (file names)
- **Error handling**: HTTPException for API, try/catch with logging, proper status codes
- **Components**: Use Shadcn/ui components, Framer Motion for animations, proper TypeScript interfaces
