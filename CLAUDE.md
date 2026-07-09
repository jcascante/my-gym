# CLAUDE.md

Guidance for developing **MyGym** — a personalized workout program manager. Users complete onboarding, get AI-generated programs, and track daily workouts with feedback.

## Stack: React 19 + FastAPI + PostgreSQL + Docker

**Backend**: FastAPI (async), Pydantic V2, SQLAlchemy 2.0+ async, Alembic migrations, pytest  
**Frontend**: React + TypeScript, Vite, Zustand, TanStack Query, Vitest  
**Database**: PostgreSQL (prod), SQLite (testing)  
**Testing**: TDD - write tests before code (>80% coverage)  
**Quality**: Ruff, Black, mypy (strict), ESLint, Prettier, pre-commit hooks

## Core Domain

**MyGym MVP**: User auth → onboarding (profile + goals) → AI program generation → daily tracking + feedback

**Key Models**: User, UserProfile, WorkoutProgram, Workout (daily), Exercise, UserWorkoutLog, Feedback  
**Key Flows**: Signup/Login → Onboarding → Create Program → Track Workouts → View Progress  
See [PROJECT_SCOPE.md](./PROJECT_SCOPE.md) for full data models and features.

## Architecture

Independent Docker services:
- **Frontend** (5173 dev) → REST /api/v1/ → **Backend** (8000)
- **Backend** → async SQLAlchemy → **PostgreSQL** (5432)
- **Program Engine**: Rules-based (templates + user data → exercise schedule)
- **Docs**: http://localhost:8000/docs (Swagger UI, auto-generated)

## Quick Commands

```bash
# Start development (all services with Docker Compose)
docker-compose up

# Backend
docker-compose exec backend pytest              # Run tests
docker-compose exec backend ruff check . --fix  # Lint
docker-compose exec backend black .             # Format
docker-compose exec backend mypy app/           # Type check
docker-compose exec backend alembic upgrade head # Migrations

# Frontend
docker-compose exec frontend npm run test:watch # Tests
docker-compose exec frontend npm run lint -- --fix # Lint
docker-compose exec frontend npm run format     # Format
docker-compose exec frontend npm run type-check # Type check

# Database
docker-compose exec postgres psql -U postgres -d app_db
```

## Key Patterns

- **Async/await**: All I/O (database, HTTP, file)
- **Type hints**: Strict mypy on backend, TypeScript on frontend
- **Testing**: TDD (test first), >80% coverage, factories + mocks
- **API**: REST v1 at `/api/v1/`, JWT auth, consistent responses
- **Migrations**: Alembic for schema, always test up/down
- **Errors**: Custom exceptions with clear context
- **Program Generation**: Rules-based (template selection → exercise assignment → progression)
- **Workout Tracking**: Immutable logs (append-only for audit trail)

## Setup

```bash
# One-time setup
git clone <repo> && cd my-gym
docker-compose up  # Starts everything

# Access points:
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# Backend docs: http://localhost:8000/docs
# Database: localhost:5432
```

## Project Structure

**Backend**: `backend/app/` 
- `models/` - SQLAlchemy models (User, UserProfile, WorkoutProgram, Workout, Exercise, UserWorkoutLog)
- `schemas/` - Pydantic schemas (request/response types)
- `api/v1/endpoints/` - Routes (auth, user, programs, workouts, logs, feedback)
- `services/` - Business logic (program generation, tracking)
- `crud/` - Database operations
- `core/` - Config, security, custom exceptions

**Frontend**: `frontend/src/`
- `components/` - Reusable components (forms, cards, charts)
- `pages/` - Route pages (login, onboarding, dashboard, tracking)
- `api/` - API client functions
- `hooks/` - Custom hooks (useProgram, useTracking, useUser)
- `store/` - Zustand stores (auth, user, workout)
- `types/` - TypeScript interfaces

**Tests**: `backend/tests/`, `frontend/src/tests/` (unit + integration)  
**Migrations**: `backend/migrations/` (Alembic version control)  
**Docs**: `PROJECT_SCOPE.md` (features + data models), `README.md` (quickstart)

## MyGym-Specific Patterns

**Program Generation**:
- User data (goals, experience, time) → Program template selection
- Template defines exercise ordering, sets/reps ranges, progression
- Store program as immutable WorkoutProgram + Workout records
- Allow manual exercise substitutions (e.g., bench press → dumbbell press)

**Workout Tracking**:
- UserWorkoutLog is append-only (for audit trail)
- Track actual weight/reps per set (arrays for flexibility)
- Feedback collected separately (optional, for UX insights)
- Daily view shows scheduled vs actual performance

**Authentication**:
- JWT in HTTP-only cookies
- Refresh token rotation on use
- Protect routes with Depends(get_current_user)

## Skills & Patterns

Use `.claude/skills/` for detailed guidance:
- `api-testing` - Backend testing patterns
- `react-component-testing` - Frontend testing patterns  
- `fastapi-async-patterns` - Async/await, dependency injection
- `react-typescript-patterns` - React + TypeScript patterns
- `rest-api-design` - API standards, status codes, error handling
- `database-migrations` - Schema change workflows
- `docker-workflows` - Docker operations
- `code-quality` - Linting, formatting, pre-commit hooks
- `token-optimization` - Token cost reduction strategies

See `.claude/skills/README.md` for full list and usage.
