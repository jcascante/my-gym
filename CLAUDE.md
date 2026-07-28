# CLAUDE.md

Guidance for developing **MyGym** — a personalized workout program manager. Users complete onboarding, get AI-generated programs, and track daily workouts with feedback.

## Core Domain

**MyGym MVP**: User auth → onboarding (profile + goals) → AI program generation → daily tracking + feedback

**Key Models**: User, UserProfile, WorkoutProgram, Workout (daily), Exercise, UserWorkoutLog, Feedback
**Key Flows**: Signup/Login → Onboarding → Create Program → Track Workouts → View Progress
See [PROJECT_SCOPE.md](./PROJECT_SCOPE.md) for full data models and features.

## Quick Commands

```bash
# Start development (all services with Docker Compose)
docker-compose up

# Backend
docker-compose exec backend pytest                                        # Run tests
docker-compose exec backend ruff check . --fix                            # Lint
docker-compose exec backend black .                                       # Format
docker-compose exec backend mypy app/                                     # Type check
docker-compose exec backend alembic upgrade head                          # Migrations
docker-compose exec backend python -m app.db.seed.seed_exercises         # Seed/update exercise library
docker-compose exec backend python -m app.db.seed.seed_program_templates # Seed program templates (run after seed_exercises)

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

See `.claude/skills/README.md` for full list and usage.

## Development Workflow

For small, well-scoped features and bug fixes, use `/build-feature`. See `.claude/commands/build-feature.md` for details.
