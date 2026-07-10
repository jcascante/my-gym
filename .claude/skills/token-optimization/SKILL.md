---
name: token-optimization
description: Optimize LLM token usage through prompt caching, context management, and efficient patterns
skills: [optimization, performance, caching]
allowed-tools: [Read, Edit, Write]
---

# Token Usage Optimization

Minimize token consumption while maintaining code quality and AI reasoning capability.

## Token Cost Breakdown (Approximate)

For Claude 3.5 Sonnet:
- System prompt: ~1,500-2,000 tokens (loaded once per session)
- CLAUDE.md: ~1,500-3,000 tokens (auto-loaded every turn)
- Skills: ~500-1,000 tokens per invoked skill
- Context window: Full conversation history (grows each turn)
- Code files read: 1 token per word (~5 chars)
- API responses: Full response size in tokens
- Thinking blocks: Can consume 20-50% of request tokens

## 1. System Prompt Optimization

### ❌ DON'T (Bloated)
```python
# app/core/config.py
SYSTEM_PROMPT = """
You are an expert full-stack developer. You should:
- Always write tests first
- Follow TDD methodology
- Use async/await for all I/O
- Never use synchronous database calls
- Always type hint your functions
- Write docstrings for all public functions
- Use error handling everywhere
- Follow PEP 8 style guide
- Use black for formatting
- Use ruff for linting
... [100+ lines of verbose instructions]
"""
```

### ✅ DO (Lean & Focused)
```python
# app/core/config.py
SYSTEM_PROMPT = """
Stack: React 19 + FastAPI + PostgreSQL + Docker. TDD first.

Backend: Async FastAPI with Pydantic V2, SQLAlchemy 2.0+, async tests (pytest).
Frontend: React + TypeScript, Vitest + Testing Library, TanStack Query.
Database: Alembic migrations, PostgreSQL primary, SQLite for testing.
Quality: Ruff, Black, mypy (strict), ESLint, Prettier. Pre-commit hooks required.

Patterns: Async/await everywhere, type hints strict, REST API standards.
Testing: Write test before code. Use factories, mocks (MSW), cover error cases.
Docs: See .claude/CLAUDE.md for architecture. Skills in .claude/skills/ for details.
"""
```

**Token savings**: ~1,000 tokens per session

## 2. CLAUDE.md Size Optimization

Current CLAUDE.md should be **under 2,000 tokens** (lean reference, not exhaustive).

### Optimization Strategy

Move detailed content to skills:
- ✅ Keep in CLAUDE.md: Architecture overview, quick command reference
- ❌ Move to skills: Detailed patterns, code examples, best practices

### Lean CLAUDE.md Structure

```markdown
# CLAUDE.md (Optimized)

This file provides guidance to Claude Code.

## Stack: React 19 + FastAPI + PostgreSQL + Docker

Backend: Async FastAPI, Pydantic V2, SQLAlchemy async, Alembic migrations, pytest
Frontend: React + TypeScript, Vite, Zustand, TanStack Query, Vitest
Quality: Ruff, Black, mypy, ESLint, Prettier, pre-commit hooks

## Quick Commands

Backend:
- docker-compose exec backend pytest
- docker-compose exec backend ruff check . --fix
- docker-compose exec backend alembic upgrade head

Frontend:
- docker-compose exec frontend npm run test:watch
- docker-compose exec frontend npm run lint -- --fix

## Architecture

- Independent Docker containers (separate deployment)
- REST API v1 at /api/v1/
- Async/await for all I/O, type hints required
- Test-first development (TDD)

## Skills

Use for detailed patterns: api-testing, fastapi-async-patterns, react-typescript-patterns
See .claude/skills/README.md

## Key Files

- Backend entry: backend/app/main.py
- Frontend entry: frontend/src/App.tsx
- Migrations: backend/migrations/
- Tests: backend/tests/, frontend/src/tests/
```

**Token savings**: ~1,500-2,000 tokens per session

## 3. Prompt Caching Strategy (FastAPI)

Enable prompt caching for frequently-accessed patterns:

### Structured API Endpoints

```python
# app/api/v1/endpoints/users.py
"""
Consistent endpoint pattern enables caching:
- GET /api/v1/users (list)
- POST /api/v1/users (create)
- GET /api/v1/users/{id} (get)
- PATCH /api/v1/users/{id} (update)
- DELETE /api/v1/users/{id} (delete)

Request/Response schema always consistent.
"""

from fastapi import APIRouter
from app.schemas import UserSchema, UserCreateSchema

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=list[UserSchema])
async def list_users(skip: int = 0, limit: int = 10):
    """List users. Consistent pattern enables caching."""
    pass

@router.post("", response_model=UserSchema, status_code=201)
async def create_user(user: UserCreateSchema):
    """Create user. Repeated across endpoints."""
    pass
```

**Cache benefit**: Repeated API patterns (CRUD operations) can use cache hits if structure is consistent.

## 4. Context Management

### Don't Read Large Files Unless Needed

```python
# ❌ DON'T: Auto-read all files
claude = ClaudeCode()
# This might load 100+ KB of code

# ✅ DO: Read only what's needed
claude.read_file("backend/app/models/users.py")  # Only 2KB
# Then: only if you need related file
claude.read_file("backend/app/schemas.py")       # Only 1.5KB
```

### Smart File Navigation

When Claude asks about a file:
1. **Read only the specific function/class** - not the whole file
2. **Ask for file structure first** - grep for function names, then read specific ones
3. **Use line numbers** - specify start/end lines to limit context

```bash
# ✅ DO: Get structure first
grep -n "^class\|^def " backend/app/models/users.py
# Output shows line numbers for specific items

# Then read only needed parts
# (Claude reads lines 10-30, not whole file)
```

## 5. Response Streaming

### Stream Responses Instead of Loading All at Once

**Frontend**:
```typescript
// ✅ DO: Use streaming for large responses
const response = await fetch('/api/v1/data');
const reader = response.body?.getReader();

if (reader) {
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    processChunk(new TextDecoder().decode(value));
  }
}

// ❌ DON'T: Load entire response
const data = await response.json();  // Waits for all data
```

**Backend**:
```python
from fastapi.responses import StreamingResponse

@app.get("/stream")
async def stream_data():
    async def generate():
        for i in range(1000):
            yield f"data: {i}\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Token savings**: Only pay for streamed data as it's generated, not buffered.

## 6. Efficient Tool Results

### Cap API Response Sizes

```python
# app/api/v1/endpoints/users.py

@router.get("", response_model=PaginatedResponse[UserSchema])
async def list_users(
    page: int = Query(1),
    limit: int = Query(10, le=100),  # ✅ Cap at 100 items
):
    """Limited response size."""
    pass

@router.get("/{id}")
async def get_user(id: int):
    """Single resource - minimal overhead."""
    pass
```

### Truncate Error Messages

```python
# ✅ DO: Concise errors (Claude understands context)
raise HTTPException(
    status_code=400,
    detail="Email already exists"
)

# ❌ DON'T: Verbose errors (wastes tokens)
raise HTTPException(
    status_code=400,
    detail=f"The email address {email} is already registered in our system. Please use a different email address or try the password reset feature if you've forgotten your login credentials."
)
```

## 7. Context Window Management

### Use `/compact` Proactively

For long conversations:
```bash
# When context reaches 70% usage
/compact

# Claude will summarize earlier context
# Continuation starts fresh with summary
```

### Don't Keep Entire Conversation History

```python
# ✅ DO: Archive old sessions
# Sessions >50MB are candidates for archival
claude rm <old-session-id>

# Start fresh session
claude --clear

# ❌ DON'T: Keep massive conversations alive
# Resume session with 100K tokens of history = expensive per turn
```

## 8. Memory & Auto-Memory Optimization

### Keep Memory Index Lean

```markdown
# MEMORY.md (Optimized)

## Project Info
- Stack: React 19 + FastAPI + PostgreSQL
- Key patterns: async/await, TDD, Docker
- Important files: See CLAUDE.md

## Development Notes
- [Use skills for patterns](./skills/)
- Migrations in backend/migrations/
- Tests: pytest (backend), vitest (frontend)
```

**Token savings**: ~500 tokens per turn if memory is well-maintained

### Disable Auto-Memory if Not Needed

```bash
# In settings.json or via /config
# Disable auto-memory if too much noise
# "autoMemory": false  # Default is true
```

## 9. Smart Skill Loading

### Invoke Skills Only When Needed

```bash
# ✅ Efficient: Request skill context only for relevant tasks
"Write a test for UserService using the api-testing skill"

# ❌ Wasteful: Load all skills at start
# Don't load all skills in system prompt
```

### Skills Loaded On-Demand

- Skills are loaded only when explicitly requested or contextually relevant
- ~500-1,000 tokens per skill × frequency = significant savings
- Core skills loaded for task (e.g., api-testing when testing)

## 10. Database Query Optimization (Indirect Token Savings)

```python
# ❌ DON'T: Multiple round-trips (more debugging output)
user = await db.get(User, user_id)
posts = await db.execute(select(Post).filter(Post.user_id == user_id))

# ✅ DO: Optimized queries (less error output, cleaner results)
user = await db.execute(
    select(User)
    .options(selectinload(User.posts))
    .filter(User.id == user_id)
)
```

## 11. Test Data Optimization

### Use Minimal Fixtures

```python
# ❌ DON'T: Huge fixture files
@pytest.fixture
def sample_users():
    return [
        {"id": i, "name": f"User {i}", "email": f"user{i}@test.com", ...}
        for i in range(1000)  # 1000 users = lots of tokens!
    ]

# ✅ DO: Generate minimal test data
@pytest.fixture
def sample_user():
    return {"id": 1, "name": "Test User", "email": "test@test.com"}

@pytest.fixture
def sample_users(sample_user):
    return [sample_user] * 3  # 3 users for testing lists
```

## 12. Configuration & Env Files

### Lean .env Configuration

```bash
# ✅ DO: Only necessary variables
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET=...
API_PORT=8000

# ❌ DON'T: Document everything in .env
# Put documentation in README or config.py docstrings instead
```

## Quick Token Savings Checklist

| Strategy | Tokens Saved | Frequency |
|----------|--------------|-----------|
| Lean system prompt | ~1,000 | Every session |
| Optimized CLAUDE.md | ~1,500-2,000 | Every session |
| On-demand skill loading | ~500-1,000 | Per skill use |
| Limited API responses | ~200-500 | Per request |
| Concise error messages | ~100-300 | Per error |
| Prompt caching (repeated patterns) | ~20-30% | On cache hit |
| Memory optimization | ~500 | Per turn |
| Context compaction | ~30-50% | On compact |

**Total potential savings: ~5,000-8,000 tokens per typical session** ✅

## Implementation Priority

1. **Week 1**: Optimize CLAUDE.md and system prompt (~3,000 tokens saved)
2. **Week 2**: Enable prompt caching on API endpoints (~2,000 tokens saved)
3. **Week 3**: Implement context management best practices (~1,000 tokens saved)
4. **Week 4**: Memory optimization and monitoring (~1,000 tokens saved)

## Monitoring Token Usage

```bash
# Track token usage per session
claude /usage

# Monitor trends
claude /stats

# Export session cost analysis
claude /export --include-tokens
```

## Best Practices Summary

- ✅ Keep CLAUDE.md under 2,000 tokens
- ✅ System prompt under 500 tokens (lean)
- ✅ Load skills on-demand, not upfront
- ✅ Read only necessary files/lines
- ✅ Limit API response sizes
- ✅ Use `/compact` at 70% context
- ✅ Maintain lean memory/MEMORY.md
- ✅ Stream large responses
- ✅ Cache repeated patterns
- ✅ Monitor usage regularly with `/usage`
