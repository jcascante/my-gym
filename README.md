# MyGym - Personalized Workout Program Manager

A modern web application that creates custom workout programs tailored to each user's fitness goals, experience level, and available time. Track daily workouts, log performance metrics, and get adaptive feedback to optimize your training.

## Features

### 🏋️ Smart Program Builder
- Generates personalized workout programs based on user goals and preferences
- Adapts to available equipment, time, and experience level
- Includes exercise form guidance and safety notes

### 📱 Daily Workout Tracking
- View today's workout with detailed exercise instructions
- Log sets, reps, and weight for each exercise
- Rate difficulty and note any pain or issues
- Quick feedback on energy level and form quality

### 📊 Progress Analytics
- Track performance trends over time
- Visual progress indicators
- Completion rate and volume metrics
- Identify patterns in workout difficulty

### 🎯 User-Focused Onboarding
- Collect personal fitness profile (goals, experience, equipment)
- Support for users at all fitness levels
- Easy profile updates for creating new programs

## Tech Stack

- **Backend**: FastAPI (async), SQLAlchemy 2.0, Pydantic V2, pytest
- **Frontend**: React 19, TypeScript, Vite, TanStack Query, Zustand
- **Database**: PostgreSQL (production), SQLite (testing)
- **Quality**: Ruff, Black, mypy, ESLint, Prettier, pre-commit hooks
- **Deployment**: Docker & Docker Compose

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Setup & Run

```bash
# Clone and navigate
git clone <repo> && cd my-gym

# Start all services
docker-compose up

# Services available at:
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs (Swagger UI)
```

### Development Commands

```bash
# Backend
docker-compose exec backend pytest                      # Run tests
docker-compose exec backend ruff check . --fix          # Lint
docker-compose exec backend black .                     # Format
docker-compose exec backend mypy app/                   # Type check

# Frontend
docker-compose exec frontend npm run test:watch         # Tests (watch mode)
docker-compose exec frontend npm run lint -- --fix      # Lint
docker-compose exec frontend npm run format             # Format

# Database
docker-compose exec backend alembic upgrade head        # Run migrations
docker-compose exec backend alembic revision --autogenerate -m "description"  # Create migration
docker-compose exec postgres psql -U postgres -d app_db # Connect to DB
```

## Project Structure

```
my-gym/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── api/v1/
│   │   │   ├── endpoints/     # Route handlers
│   │   │   └── dependencies/  # FastAPI dependencies
│   │   ├── services/          # Business logic
│   │   ├── crud/              # Database operations
│   │   └── core/              # Config, security, exceptions
│   ├── tests/                 # Pytest test suite
│   ├── migrations/            # Alembic schema migrations
│   └── Dockerfile
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── api/               # API client functions
│   │   ├── hooks/             # Custom React hooks
│   │   ├── store/             # Zustand state
│   │   ├── types/             # TypeScript types
│   │   └── tests/             # Vitest tests
│   └── Dockerfile
├── docker-compose.yml         # Multi-service orchestration
├── CLAUDE.md                  # Development guidance
├── PROJECT_SCOPE.md           # MVP features & data models
└── README.md                  # This file
```

## Development Workflow

1. **Plan** - Review `PROJECT_SCOPE.md` for requirements
2. **Test First** - Write tests before implementation (TDD)
3. **Implement** - Follow patterns in `.claude/skills/`
4. **Quality Check** - Lint, format, type check
5. **Commit** - Clear commit messages

## Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Development guidelines, tech stack, key patterns
- **[PROJECT_SCOPE.md](./PROJECT_SCOPE.md)** - MVP features, data models, API endpoints
- **[.claude/skills/](.//.claude/skills/)** - Detailed patterns for specific domains
  - API testing, React components, database migrations, FastAPI async, etc.

## API Overview

All endpoints use the `/api/v1/` prefix and JWT authentication.

### Authentication
- `POST /auth/signup` - Register
- `POST /auth/login` - Login
- `POST /auth/refresh` - Refresh token

### User Management
- `GET /user/profile` - Get user profile
- `PUT /user/profile` - Update profile
- `GET /user/programs` - List programs

### Workout Programs
- `POST /programs` - Create new program
- `GET /programs/{id}` - Get program details
- `GET /programs/{id}/workouts` - List workouts in program
- `PUT /programs/{id}` - Update program

### Workout Tracking
- `GET /programs/{id}/workouts/{day}` - Get today's workout
- `POST /workouts/{id}/log` - Log completed workout
- `POST /workouts/{id}/feedback` - Submit feedback

See [PROJECT_SCOPE.md](./PROJECT_SCOPE.md) for complete API documentation.

## Key Patterns

### Backend
- **Async/await** for all I/O operations
- **Type hints** with strict mypy checking
- **Pydantic** for request/response validation
- **SQLAlchemy** async ORM for database
- **Dependency injection** for testability

### Frontend
- **TypeScript** for type safety
- **React hooks** for component logic
- **TanStack Query** for server state
- **Zustand** for client state
- **User-centric testing** with React Testing Library

## Testing

### Backend (pytest)
```bash
# Run all tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app

# Run specific test
docker-compose exec backend pytest tests/test_auth.py
```

### Frontend (Vitest)
```bash
# Run tests
docker-compose exec frontend npm run test

# Watch mode
docker-compose exec frontend npm run test:watch

# With coverage
docker-compose exec frontend npm run test:coverage
```

**Target**: >80% code coverage for both frontend and backend

## Code Quality

All code is automatically checked via pre-commit hooks:
- **Python**: ruff (linting), black (formatting), mypy (type checking)
- **TypeScript/React**: ESLint (linting), Prettier (formatting)

Run checks manually:
```bash
# Backend
docker-compose exec backend ruff check . --fix
docker-compose exec backend black .
docker-compose exec backend mypy app/

# Frontend
docker-compose exec frontend npm run lint -- --fix
docker-compose exec frontend npm run format
docker-compose exec frontend npm run type-check
```

## Authentication & Security

- **JWT tokens** for stateless authentication
- **HTTP-only cookies** for token storage on frontend
- **CORS** configured for frontend origin only
- **Password hashing** with bcrypt
- **HTTPS** recommended for production

## Environment Variables

See `.env.example` for configuration template:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/app_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
VITE_API_URL=http://localhost:8000
```

## Troubleshooting

### Docker Services Won't Start
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Database Connection Issues
```bash
# Connect directly to postgres
docker-compose exec postgres psql -U postgres -d app_db

# Check migrations status
docker-compose exec backend alembic current
docker-compose exec backend alembic history
```

### Port Conflicts
If ports 5173, 8000, or 5432 are already in use:
1. Edit `docker-compose.yml` to use different host ports
2. Update `.env` VITE_API_URL if changing backend port

## Contributing

1. Create feature branch from `main`
2. Write tests first (TDD)
3. Implement feature
4. Run quality checks
5. Commit with clear message
6. Create pull request

## Performance Targets

- Program generation: <2 seconds
- API response time: <500ms (p95)
- Frontend load time: <3 seconds (3G)
- Daily tracking: <3 minutes per workout

## Future Enhancements

- Social features (friends, challenges)
- Advanced analytics with ML predictions
- Nutrition tracking
- Video form demonstrations
- Wearable device integration
- Mobile app
- Admin dashboard

## Support

For issues or questions:
1. Check `.claude/skills/` for development patterns
2. Review `PROJECT_SCOPE.md` for requirements
3. Consult `CLAUDE.md` for architecture guidelines

## License

[To be determined]
