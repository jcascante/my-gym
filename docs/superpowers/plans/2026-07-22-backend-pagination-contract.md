# Backend Pagination Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement backend pagination support for the `/programs/match` endpoint to complete the infinite scroll feature and match the frontend contract.

**Architecture:** Update the existing `/programs/match` endpoint to accept `limit` and `offset` query parameters, implement server-side pagination using the existing `rank_templates()` function (which already supports pagination), and return the `TemplateMatchResponse` schema (which already exists in code). The frontend implementation is complete; this fills the missing backend half.

**Tech Stack:** FastAPI, Pydantic V2, SQLAlchemy 2.0+, pytest

## Global Constraints

- Backend follows async/await patterns for all I/O
- All code must pass `mypy --strict` type checking
- All code must pass `ruff check` linting and `black` formatting
- Tests use pytest with >80% coverage
- API responses use consistent `TemplateMatchResponse` schema
- Query parameters: `limit` (optional, ge=0), `offset` (optional, ge=0, default=0)
- Default limit when not provided: use config value (currently 4)

---

## File Structure

**Files to modify:**
- `backend/app/api/v1/endpoints/programs.py` — The `/match` endpoint (currently line 110-182)
- `backend/tests/test_programs_flow.py` — Integration tests for the endpoint
- `backend/tests/test_matching.py` — Unit tests for pagination behavior (if needed)

**Files already correct (no changes needed):**
- `backend/app/schemas/program_api.py` — `TemplateMatchResponse` already defined
- `backend/app/services/program/matching.py` — `rank_templates()` already supports `limit`/`offset`

---

### Task 1: Write Tests for Pagination Query Parameters

**Files:**
- Modify: `backend/tests/test_programs_flow.py`
- Test: Existing test file

**Interfaces:**
- Consumes: Current `/match` endpoint (before changes)
- Produces: Test cases that specify:
  - Query parameter parsing (limit, offset)
  - Response shape validation
  - Pagination behavior

- [ ] **Step 1: Write test for initial load (no pagination params)**

Add to `backend/tests/test_programs_flow.py`:

```python
@pytest.mark.asyncio
async def test_match_endpoint_returns_default_batch_size(client: TestClient):
    """Match endpoint without limit/offset returns default batch size."""
    response = client.post(
        "/api/v1/programs/match",
        json={
            "environment_id": 1,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert "total_count" in data
    assert "offset" in data
    assert "limit" in data
    assert data["offset"] == 0
    assert data["limit"] == 4  # Default batch size
    assert len(data["matches"]) <= 4
```

- [ ] **Step 2: Write test for pagination with limit and offset**

```python
@pytest.mark.asyncio
async def test_match_endpoint_with_limit_and_offset(client: TestClient):
    """Match endpoint accepts limit and offset query params."""
    response = client.post(
        "/api/v1/programs/match?limit=3&offset=4",
        json={
            "environment_id": 1,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["offset"] == 4
    assert data["limit"] == 3
    assert len(data["matches"]) <= 3
    # Verify it's a slice, not all results
    assert data["total_count"] >= len(data["matches"])
```

- [ ] **Step 3: Write test for invalid query params**

```python
@pytest.mark.asyncio
async def test_match_endpoint_rejects_negative_limit(client: TestClient):
    """Match endpoint rejects negative limit."""
    response = client.post(
        "/api/v1/programs/match?limit=-1&offset=0",
        json={
            "environment_id": 1,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == 422  # Validation error
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_programs_flow.py::test_match_endpoint_returns_default_batch_size -xvs
pytest tests/test_programs_flow.py::test_match_endpoint_with_limit_and_offset -xvs
pytest tests/test_programs_flow.py::test_match_endpoint_rejects_negative_limit -xvs
```

Expected: All 3 tests FAIL (endpoint doesn't support pagination yet)

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_programs_flow.py
git commit -m "test(backend): add pagination query parameter tests for match endpoint"
```

---

### Task 2: Update Match Endpoint to Accept Pagination Parameters

**Files:**
- Modify: `backend/app/api/v1/endpoints/programs.py:110-182` (the `match` function)
- Test: Tests from Task 1

**Interfaces:**
- Consumes:
  - Existing endpoint logic (template fetching, feasibility checking, scoring)
  - `rank_templates(..., limit, offset)` already supports pagination
  - `Query(limit, offset)` from FastAPI
- Produces:
  - Updated `/match` endpoint that passes `limit`/`offset` to `rank_templates()`
  - Response shape: `TemplateMatchResponse` with matches, total_count, offset, limit

- [ ] **Step 1: Add query parameters to endpoint signature**

Modify `backend/app/api/v1/endpoints/programs.py` line 111:

```python
@router.post("/match", response_model=TemplateMatchResponse)
async def match(
    data: MatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine_config: EngineConfig = Depends(get_engine_config),
    limit: int | None = Query(None, ge=0),  # NEW: query parameter
    offset: int = Query(0, ge=0),  # NEW: query parameter
) -> TemplateMatchResponse:
```

- [ ] **Step 2: Pass pagination params to rank_templates**

Modify line 144 in the same function, in the `rank_templates()` call:

```python
    result = rank_templates(
        templates,
        inp,
        feasibility,
        definitions=definitions,
        all_exercises=exercises,
        config=engine_config,
        limit=limit,  # CHANGED: pass limit from query param
        offset=offset,  # CHANGED: pass offset from query param
    )
```

- [ ] **Step 3: Calculate effective limit for response**

Modify line 176 (after the rank_templates call, before the return):

```python
    effective_limit = limit if limit is not None else engine_config.max_template_matches
    return TemplateMatchResponse(
        matches=matches,
        total_count=result.total_count,
        offset=offset,
        limit=effective_limit,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_programs_flow.py::test_match_endpoint_returns_default_batch_size -xvs
pytest tests/test_programs_flow.py::test_match_endpoint_with_limit_and_offset -xvs
pytest tests/test_programs_flow.py::test_match_endpoint_rejects_negative_limit -xvs
```

Expected: All 3 tests PASS

- [ ] **Step 5: Run full backend test suite**

```bash
cd backend
pytest tests/ -xvs
mypy app/
black app/ tests/
ruff check app/ tests/
```

Expected: All tests pass, type-check clean, linting clean

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/endpoints/programs.py backend/tests/test_programs_flow.py
git commit -m "feat(backend): add limit/offset pagination parameters to match endpoint"
```

---

### Task 3: Verify Backend-Frontend Contract Integration

**Files:**
- Modify: `backend/tests/test_programs_flow.py`
- Test: New integration test

**Interfaces:**
- Consumes:
  - Updated `/match` endpoint from Task 2
  - Frontend expectations: `limit=4, offset=0` for initial, `limit=3, offset=4` for pagination
- Produces:
  - Integration test verifying full pagination flow

- [ ] **Step 1: Write full pagination flow test**

Add to `backend/tests/test_programs_flow.py`:

```python
@pytest.mark.asyncio
async def test_match_endpoint_pagination_flow_full_sequence(client: TestClient):
    """Test complete pagination flow: initial batch (4) → next batch (3) → end."""
    # Assume enough templates exist in test db (10+ total)
    req = {
        "environment_id": 1,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "general",
        "duration_weeks": 8,
    }

    # Step 1: Initial load (offset=0, limit=4)
    resp1 = client.post("/api/v1/programs/match?limit=4&offset=0", json=req)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["matches"]) == 4
    assert data1["offset"] == 0
    assert data1["limit"] == 4
    total_count = data1["total_count"]

    # Step 2: Next batch (offset=4, limit=3)
    resp2 = client.post("/api/v1/programs/match?limit=3&offset=4", json=req)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["matches"]) == 3
    assert data2["offset"] == 4
    assert data2["limit"] == 3
    assert data2["total_count"] == total_count  # Same total

    # Step 3: Verify no duplicates (different template IDs)
    ids1 = {m["template_id"] for m in data1["matches"]}
    ids2 = {m["template_id"] for m in data2["matches"]}
    assert len(ids1 & ids2) == 0, "Pagination returned duplicate templates"
```

- [ ] **Step 2: Run test to verify full flow**

```bash
cd backend
pytest tests/test_programs_flow.py::test_match_endpoint_pagination_flow_full_sequence -xvs
```

Expected: PASS

- [ ] **Step 3: Run all backend tests**

```bash
cd backend
pytest tests/ -q
```

Expected: All tests pass (no regressions)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_programs_flow.py
git commit -m "test(backend): add full pagination flow integration test for match endpoint"
```

---

### Task 4: Test Frontend-Backend Contract (Non-Mocked Integration)

**Files:**
- Create: `backend/tests/test_pagination_contract.py` (optional, for extra verification)
- Modify: `backend/tests/test_programs_flow.py`

**Interfaces:**
- Consumes:
  - Updated `/match` endpoint
  - Frontend response parsing expectations
- Produces:
  - Validation that response exactly matches what frontend expects

- [ ] **Step 1: Write contract validation test**

Add to `backend/tests/test_programs_flow.py`:

```python
@pytest.mark.asyncio
async def test_match_response_matches_frontend_contract(client: TestClient):
    """Verify match response schema exactly matches frontend TemplateMatchResponse."""
    response = client.post(
        "/api/v1/programs/match?limit=4&offset=0",
        json={
            "environment_id": 1,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Verify schema has exactly what frontend expects
    required_fields = {"matches", "total_count", "offset", "limit"}
    assert set(data.keys()) >= required_fields

    # Verify matches array structure
    assert isinstance(data["matches"], list)
    if data["matches"]:
        match = data["matches"][0]
        required_match_fields = {
            "template_id",
            "slug",
            "name",
            "fit_pct",
            "factors",
            "required_inputs",
            "tier",
            "all_infeasible",
            "advisories",
        }
        assert set(match.keys()) >= required_match_fields

    # Verify scalar fields are correct types
    assert isinstance(data["total_count"], int)
    assert isinstance(data["offset"], int)
    assert isinstance(data["limit"], int)
```

- [ ] **Step 2: Run contract test**

```bash
cd backend
pytest tests/test_programs_flow.py::test_match_response_matches_frontend_contract -xvs
```

Expected: PASS

- [ ] **Step 3: Run full suite one final time**

```bash
cd backend
pytest tests/ -q
mypy app/
black --check app/ tests/
ruff check app/ tests/
```

Expected: All passing

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_programs_flow.py
git commit -m "test(backend): verify match response matches frontend contract"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✓ Accept `limit`/`offset` query parameters (Task 2)
- ✓ Implement server-side pagination (Task 2, uses existing `rank_templates()`)
- ✓ Return `TemplateMatchResponse` with `total_count`, `offset`, `limit` (Task 2, response line)
- ✓ Tests verify pagination works correctly (Task 1, 3, 4)

**Placeholder scan:**
- ✓ No TBD, TODO, or incomplete sections
- ✓ All test code is complete and exact
- ✓ All implementation code is complete and exact
- ✓ All commands are exact with expected output

**Type consistency:**
- ✓ `limit: int | None = Query(None, ge=0)` matches frontend usage
- ✓ `offset: int = Query(0, ge=0)` matches frontend usage
- ✓ Response `TemplateMatchResponse` exactly matches schema definition

---

## Plan Status

**Tasks:** 4 (backend-only, focused scope)
**Estimated effort:** 1-2 hours for an experienced developer
**Risk level:** Low (modifying existing endpoint that already has pagination support internally)
**Dependencies:** None (can be done independently; completes the frontend work)

---

Plan complete and saved to `docs/superpowers/plans/2026-07-22-backend-pagination-contract.md`.

**Execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
