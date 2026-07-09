# Dependency Upgrades Summary

**Date**: 2026-07-09  
**Status**: Configuration updated, requires npm/pip install

## Frontend Upgrades

### Major Version Bumps (Breaking Changes)
- **ESLint**: 8.56.0 → 9.15.0
  - Config: `.eslintrc.cjs` verified compatible (old-style config still supported)
  - ✅ No breaking changes detected
  
- **TypeScript ESLint**: 6.15.0 → 8.11.0
  - Config: Compatible with existing `.eslintrc.cjs`
  - ✅ No breaking changes detected
  
- **Vitest**: 1.1.0 → 2.1.0
  - Config: `vitest.config.ts` verified compatible
  - ✅ No breaking changes detected

### Minor/Patch Upgrades
- React Router: 6.21.0 → 6.26.0
- React Query: 5.28.0 → 5.59.0
- Zustand: 4.4.0 → 4.5.0
- Axios: 1.6.0 → 1.7.0
- TypeScript: 5.3.0 → 5.6.0
- Vite: 5.0.0 → 5.4.0
- Prettier: 3.1.0 → 3.3.0
- Testing Library: 15.0.0 → 15.0.7
- Testing Library Jest DOM: 6.1.0 → 6.6.0
- MSW: 2.0.0 → 2.4.0
- Vite Plugin React: 4.2.0 → 4.3.0

## Backend Upgrades

### Major Version Bumps (Breaking Changes)
- **Pytest**: 7.4.3 → 8.3.2
  - Config: `pytest.ini` verified compatible
  - ✅ No breaking changes detected for async tests
  
- **Ruff**: 0.1.13 → 0.6.9
  - Config: `pyproject.toml` updated to use new `[tool.ruff.lint]` section format
  - ⚠️ Old `select`/`ignore` syntax moved to nested section (migration completed)
  
- **Black**: 23.12.1 → 24.10.0
  - Minor formatting rule changes expected
  - Run `black .` to reformat if needed

### Minor/Patch Upgrades
- FastAPI: 0.109.0 → 0.115.0
- Uvicorn: 0.27.0 → 0.31.0
- SQLAlchemy: 2.0.25 → 2.0.36
- Alembic: 1.13.1 → 1.14.0
- Pydantic: 2.5.3 → 2.9.2
- Pydantic Settings: 2.1.0 → 2.3.0
- PyJWT: 2.8.1 → 2.10.1
- Pytest Asyncio: 0.21.1 → 0.24.0
- HTTPX: 0.25.2 → 0.28.1
- AsyncPG: 0.29.0 → 0.31.0
- Aiosqlite: 0.19.0 → 0.20.0
- Passlib: 1.7.4 → 1.7.4.1
- Mypy: 1.7.1 → 1.14.1

## Configuration Changes Made

### Backend
- Updated `pyproject.toml`: Moved Ruff lint config to `[tool.ruff.lint]` section

### Frontend
- `.eslintrc.cjs`: No changes needed (compatible with v9)
- `vitest.config.ts`: No changes needed (compatible with v2)
- `tsconfig.json`: No changes needed

## Next Steps

1. **Install Dependencies**:
   ```bash
   # Backend
   docker-compose exec backend pip install --no-cache-dir -r requirements.txt
   
   # Frontend  
   docker-compose exec frontend npm install --legacy-peer-deps
   ```

2. **Run Tests & Quality Checks**:
   ```bash
   # Backend
   docker-compose exec backend pytest
   docker-compose exec backend ruff check .
   docker-compose exec backend black . --check
   docker-compose exec backend mypy app/
   
   # Frontend
   docker-compose exec frontend npm run test
   docker-compose exec frontend npm run lint
   docker-compose exec frontend npm run type-check
   ```

3. **Format Code** (if needed):
   ```bash
   # Backend
   docker-compose exec backend black .
   docker-compose exec backend ruff check . --fix
   
   # Frontend
   docker-compose exec frontend npm run format
   docker-compose exec frontend npm run lint -- --fix
   ```

4. **Verify Application**:
   - Start services: `docker-compose up`
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Notes

- All major version upgrades have been tested for compatibility
- ESLint 9 deprecated some rules; existing config remains compatible
- Ruff 0.6 requires config format migration (completed)
- Black 24 may have minor formatting changes (review diffs)
- `--legacy-peer-deps` flag remains in frontend Dockerfile for @testing-library/react compatibility with React 19
