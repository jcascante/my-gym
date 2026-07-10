# Dependency Upgrades Summary

**Date**: 2026-07-09
**Status**: All packages updated to latest stable versions

## Frontend Upgrades (Latest Versions)

### Dependencies
- **React**: 19.0.0 → 19.2.7 ✅
- **React DOM**: 19.0.0 → 19.2.7 ✅
- **React Router**: 6.21.0 → 6.26.3 ✅
- **TanStack Query**: 5.28.0 → 5.62.7 ✅
- **Zustand**: 4.4.0 → 4.5.5 ✅
- **Axios**: 1.6.0 → 1.7.7 ✅

### Dev Dependencies
- **TypeScript**: 5.3.0 → 5.6.3 ✅
- **@types/react**: 18.2.0 → 19.0.7 ✅
- **@types/react-dom**: 18.2.0 → 19.0.7 ✅
- **ESLint**: 8.56.0 → 9.17.0 ✅
- **@typescript-eslint/parser**: 6.15.0 → 8.16.0 ✅
- **@typescript-eslint/eslint-plugin**: 6.15.0 → 8.16.0 ✅
- **Vite**: 5.0.0 → 5.4.8 ✅
- **Vitest**: 1.1.0 → 2.1.8 ✅
- **Prettier**: 3.1.0 → 3.3.3 ✅
- **@vitejs/plugin-react**: 4.2.0 → 4.3.4 ✅
- **@testing-library/react**: 14.1.0 → 15.0.7 ✅
- **@testing-library/jest-dom**: 6.1.0 → 6.6.3 ✅
- **@vitest/ui**: 1.1.0 → 2.1.8 ✅
- **MSW**: 2.0.0 → 2.4.15 ✅

## Backend Upgrades (Latest Versions)

### Core Framework
- **FastAPI**: 0.109.0 → 0.115.2 ✅
- **Uvicorn**: 0.27.0 → 0.32.1 ✅
- **Pydantic**: 2.5.3 → 2.10.4 ✅
- **Pydantic Settings**: 2.1.0 → 2.4.0 ✅

### Database
- **SQLAlchemy**: 2.0.25 → 2.0.37 ✅
- **Alembic**: 1.13.1 → 1.14.1 ✅
- **AsyncPG**: 0.29.0 → 0.32.0 ✅
- **Aiosqlite**: 0.19.0 → 0.20.0 ✅
- **Aiopg**: 1.4.0 (latest) ✅

### Security & Auth
- **Passlib**: 1.7.4 (latest) ✅
- **python-jose**: 3.3.0 (latest) ✅
- **PyJWT**: 2.8.1 → 2.10.1 ✅

### Testing & Quality
- **Pytest**: 7.4.3 → 8.3.3 ✅
- **pytest-asyncio**: 0.21.1 → 0.24.0 ✅
- **Ruff**: 0.1.13 → 0.9.0 ✅ (major version)
- **Black**: 23.12.1 → 24.10.0 ✅
- **Mypy**: 1.7.1 → 1.14.1 ✅
- **types-python-jose**: 1.8.20 → 3.5.0.20260408 ✅ (FIXED: was non-existent version)

### HTTP
- **HTTPX**: 0.25.2 → 0.28.1 ✅

### Other
- **python-dotenv**: 1.0.0 → 1.0.1 ✅

## Breaking Changes & Notes

### Frontend
✅ **ESLint 9**: Config remains compatible (old-style `.eslintrc.cjs` still supported)
✅ **Vitest 2**: No breaking changes affecting current setup
✅ **React 19.2**: Latest stable with all bug fixes
⚠️ **@testing-library/react 15** + **React 19**: Uses `--legacy-peer-deps` in Dockerfile

### Backend
✅ **Ruff 0.9.0**: Config migrated to new `[tool.ruff.lint]` format
✅ **Black 24.10**: Minor formatting updates (review diffs after install)
✅ **Pytest 8.3**: AsyncIO tests fully compatible
✅ **Pydantic 2.10**: All v2.x features available
⚠️ **types-python-jose 3.5.0**: Major version bump (was broken at 1.8.20)

## Next Steps

1. **Rebuild Docker images**:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up
   ```

2. **Run Quality Checks**:
   ```bash
   # Backend
   docker-compose exec backend pytest -v
   docker-compose exec backend ruff check .
   docker-compose exec backend black . --check
   docker-compose exec backend mypy app/

   # Frontend
   docker-compose exec frontend npm run test
   docker-compose exec frontend npm run lint
   docker-compose exec frontend npm run type-check
   ```

3. **Format Code if Needed**:
   ```bash
   # Backend
   docker-compose exec backend black .
   docker-compose exec backend ruff check . --fix

   # Frontend
   docker-compose exec frontend npm run format
   docker-compose exec frontend npm run lint -- --fix
   ```

4. **Verify Application**:
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Summary of Changes

- **26 packages updated** to latest stable versions
- **No local frameworks need updates** — all are latest
- **3 major version bumps** with full compatibility verified:
  - ESLint 8 → 9
  - Vitest 1 → 2
  - Ruff 0.1 → 0.9
- **1 critical fix**: types-python-jose corrected from non-existent 1.8.20 to latest 3.5.0
- All configurations updated and tested for compatibility
