# Claude Code Skills for MyGym App

This directory contains specialized skills to guide Claude Code when working on this project. Each skill provides best practices, patterns, and workflows for specific areas.

## Available Skills

### 1. **api-testing** - FastAPI Endpoint Testing
- Comprehensive testing strategy (unit, integration, fixtures)
- pytest + pytest-asyncio patterns
- Mock external services
- Test structure and organization

### 2. **react-component-testing** - React Component Testing
- User-centric testing with React Testing Library
- Vitest setup and configuration
- API mocking with MSW (Mock Service Worker)
- Testing accessibility (a11y)
- Error boundaries and async handling

### 3. **database-migrations** - Alembic Migration Management
- Safe schema change workflows
- Data migration patterns
- Backward-compatible migration strategies
- Testing migrations (up and down)
- Production deployment checklist

### 4. **docker-workflows** - Docker & Docker Compose
- Local development with Docker Compose
- Development vs production Dockerfiles
- Multi-stage builds for optimization
- Running tests in containers
- Independent service deployment

### 5. **fastapi-async-patterns** - FastAPI Best Practices
- Async/await for all I/O operations
- Dependency injection patterns
- CRUD operations with async SQLAlchemy
- Service layer business logic
- Error handling and custom exceptions
- Testing async endpoints

### 6. **react-typescript-patterns** - React + TypeScript Development
- Strict TypeScript typing for components
- Modern hooks patterns (useState, useEffect, custom hooks)
- State management with Zustand
- TanStack Query (React Query) for data fetching
- Component composition and reusability
- Error boundaries

### 7. **rest-api-design** - REST API Standards
- RESTful API design conventions
- HTTP status codes and semantics
- Consistent response formats
- Error handling and validation
- Pagination, filtering, sorting
- API versioning strategies
- Comprehensive testing patterns

### 8. **code-quality** - Code Quality & Standards
- Backend: ruff, black, mypy, pytest
- Frontend: ESLint, Prettier, TypeScript strict mode, Vitest
- Pre-commit hooks and CI/CD setup
- Coverage targets and metrics
- IDE configuration
- GitHub Actions workflows

### 9. **documentation** - User & Technical Documentation
- User documentation (feature guides, step-by-step instructions)
- Technical documentation (architecture, implementation, API reference)
- GitHub Pages structure and indexing
- Documentation patterns and templates
- Navigation and cross-linking
- Writing guidelines for different audiences

## How to Use Skills

Skills are invoked automatically when relevant to your work. You can also explicitly request them:

```
Write a test for the UserService using the api-testing skill
```

Or type the skill name as a command:
```
/api-testing
/react-component-testing
/database-migrations
/documentation
```

## Development Workflow

1. **Write tests first** (TDD) - use `api-testing` or `react-component-testing`
2. **Implement feature** - follow `fastapi-async-patterns` or `react-typescript-patterns`
3. **Run quality checks** - refer to `code-quality`
4. **Database changes** - use `database-migrations`
5. **API design** - follow `rest-api-design`
6. **Document feature** - use `documentation`
   - User documentation: How to use the feature
   - Technical documentation: Implementation details
7. **Deployment** - use `docker-workflows`

## Quick Commands

```bash
# Backend
docker-compose exec backend pytest                          # Run tests
docker-compose exec backend ruff check . --fix              # Lint
docker-compose exec backend black .                         # Format
docker-compose exec backend mypy app/                       # Type check

# Frontend
docker-compose exec frontend npm run test:watch             # Run tests
docker-compose exec frontend npm run lint -- --fix          # Lint
docker-compose exec frontend npm run format                 # Format
docker-compose exec frontend npm run type-check             # Type check

# Database
docker-compose exec backend alembic upgrade head            # Run migrations
docker-compose exec backend alembic revision --autogenerate -m "desc"  # Create migration
```

## Standards Summary

- **Testing**: TDD approach, >80% coverage required
- **Code**: Strict type checking, async/await for I/O, proper error handling
- **API**: Consistent REST patterns, proper status codes, versioned endpoints
- **Quality**: Automated linting, formatting, and type checking via pre-commit
- **Deployment**: Independent Docker services, separate frontend/backend deployment
