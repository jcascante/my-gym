# MyGym Skills Library

Specialized guides for developing MyGym (React 19 + FastAPI + PostgreSQL + Docker). Each skill provides detailed patterns, examples, and best practices for specific areas of the codebase.

## Available Skills

### Backend Development

- **[api-testing](./api-testing/SKILL.md)** — Backend testing patterns with pytest, factories, and integration tests for FastAPI endpoints
- **[fastapi-async-patterns](./fastapi-async-patterns/SKILL.md)** — Async/await best practices, dependency injection, error handling in FastAPI
- **[rest-api-design](./rest-api-design/SKILL.md)** — REST API standards, status codes, error responses, pagination, authentication
- **[database-migrations](./database-migrations/SKILL.md)** — Schema changes with Alembic, migration workflows, testing strategies

### Frontend Development

- **[react-design](./react-design/SKILL.md)** — Design system, responsive patterns, accessibility, dark mode, component structure
- **[react-typescript-patterns](./react-typescript-patterns/SKILL.md)** — Type-safe React components, custom hooks, state management (Zustand), React Query integration
- **[react-component-testing](./react-component-testing/SKILL.md)** — Component testing with Vitest and React Testing Library, accessibility testing

### Operations & Quality

- **[docker-workflows](./docker-workflows/SKILL.md)** — Docker Compose setup, local development, debugging containers, deployment patterns
- **[code-quality](./code-quality/SKILL.md)** — Linting (Ruff), formatting (Black), type checking (mypy), pre-commit hooks
- **[token-optimization](./token-optimization/SKILL.md)** — Token usage optimization strategies for Claude Code and API efficiency
- **[pause-session](./pause-session/SKILL.md)** — Save/resume progress across sessions via a small per-branch handoff file

## How to Use

### Load a Skill

Use `/skill-name` to load detailed patterns for a task:

```bash
# Before testing the backend
/api-testing

# Before building a React component
/react-typescript-patterns

# Before writing migrations
/database-migrations
```

### Example Workflow

1. **Planning** → Read `CLAUDE.md` for architecture overview
2. **Implementation** → Invoke relevant skill for patterns/examples
3. **Testing** → Use `api-testing` or `react-component-testing` skill
4. **Quality** → Run `code-quality` checks (linting, types, formatting)

## Skill Structure

Each skill is a directory with a `SKILL.md` file:

```
.claude/skills/
├── api-testing/
│   └── SKILL.md          # Patterns, examples, best practices
├── react-design/
│   └── SKILL.md
└── ... (9 more skills)
```

## When to Invoke Each Skill

| Task | Skill |
|------|-------|
| Write API endpoint tests | `api-testing` |
| Design React component | `react-design` |
| Create custom hook | `react-typescript-patterns` |
| Test React component | `react-component-testing` |
| Write async service | `fastapi-async-patterns` |
| Design API route | `rest-api-design` |
| Create database migration | `database-migrations` |
| Setup Docker Compose | `docker-workflows` |
| Run linting/formatting | `code-quality` |
| Optimize token usage | `token-optimization` |
| Pause/resume work across sessions | `pause-session` |

## Quick Reference

### Backend Stack
- **Framework**: FastAPI (async)
- **ORM**: SQLAlchemy 2.0+ async
- **Database**: PostgreSQL (prod), SQLite (testing)
- **Migrations**: Alembic
- **Testing**: pytest + factories + mocks
- **Quality**: Ruff, Black, mypy (strict)

### Frontend Stack
- **Framework**: React 19
- **Language**: TypeScript (strict)
- **Build**: Vite
- **State**: Zustand
- **Queries**: TanStack Query
- **Testing**: Vitest + React Testing Library
- **Quality**: ESLint, Prettier, TypeScript

## Development Workflow

```bash
# 1. Start Docker services
docker-compose up -d

# 2. Backend development
docker-compose exec backend pytest              # Test
docker-compose exec backend ruff check . --fix  # Lint
docker-compose exec backend black .             # Format
docker-compose exec backend mypy app/           # Type check

# 3. Frontend development
docker-compose exec frontend npm run test:watch # Test
docker-compose exec frontend npm run lint -- --fix # Lint
docker-compose exec frontend npm run format     # Format

# 4. Database migrations
docker-compose exec backend alembic revision --autogenerate -m "message"
docker-compose exec backend alembic upgrade head

# 5. Access documentation
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Key Patterns

- **Async/Await**: All I/O is async (database, HTTP, file)
- **Type Safety**: Strict mypy (backend), strict TypeScript (frontend)
- **TDD**: Write tests first, >80% coverage required
- **REST**: Consistent API at `/api/v1/` with JWT auth
- **Migrations**: Schema changes via Alembic, always test up/down
- **Components**: Reusable, testable, accessible, responsive
- **State**: Zustand for global state, React Query for server state

## Architecture

```
my-gym/
├── backend/              # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py      # Entry point
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── api/v1/      # REST endpoints
│   │   ├── services/    # Business logic
│   │   ├── crud/        # Database operations
│   │   └── core/        # Config, security
│   └── tests/           # pytest tests
├── frontend/            # React + Vite
│   ├── src/
│   │   ├── components/  # Reusable components
│   │   ├── pages/       # Route pages
│   │   ├── api/         # API client
│   │   ├── hooks/       # Custom hooks
│   │   ├── store/       # Zustand stores
│   │   └── types/       # TypeScript types
│   └── src/tests/       # Vitest tests
├── docker-compose.yml   # Local development
├── CLAUDE.md            # Architecture overview (this project)
└── .claude/skills/      # Skill library (this directory)
```

## Resources

- **Backend Docs**: http://localhost:8000/docs (Swagger UI, auto-generated)
- **Type Hints**: See `CLAUDE.md` and skill examples
- **Testing Strategy**: `api-testing` and `react-component-testing` skills
- **Code Standards**: `code-quality` skill + pre-commit hooks

## Tips

- Use skills to scaffold new features (copy pattern → adapt)
- Cross-reference skills when combining backend + frontend (e.g., API design + React hooks)
- Check `CLAUDE.md` for quick command reference
- Run linters before committing (pre-commit hooks required)
- Keep tests close to implementation (same directory structure)
