# Database Migrations Guide

This document explains how to manage database schema changes using **Alembic**, the database migration tool for SQLAlchemy.

## Overview

- **Tool**: Alembic (version control for database schemas)
- **Location**: `backend/alembic/` (config and scripts)
- **Migrations**: `backend/alembic/versions/` (versioned SQL/Python files)
- **Tracking**: Git tracks all migration files for reproducible deployments

## Initial Setup

### 1. Initialize Alembic (First Time Only)

If `backend/alembic/` doesn't exist, initialize it:

**With Docker Compose:**
```bash
docker-compose exec backend alembic init alembic
```

**Without Docker Compose:**
```bash
cd backend
alembic init alembic
cd ..
```

This creates:
- `backend/alembic/` - Alembic directory
- `backend/alembic.ini` - Configuration file
- `backend/alembic/env.py` - Environment setup (auto-detects model changes)
- `backend/alembic/versions/` - Migration files (initially empty)

### 2. Configure `alembic/env.py`

For auto-detection of model changes, update `backend/alembic/env.py`:

```python
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import Base  # Import your declarative base
from app.core.config import get_database_url  # Import your database URL

# Alembic Config object
config = context.config
fileConfig(config.config_file_name)

# Set SQLAlchemy URL
config.set_main_option("sqlalchemy.url", get_database_url())

# Set target_metadata for auto-detection
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## Workflow

### Creating a Migration

Whenever you modify SQLAlchemy models, create a migration:

**Recommended: Auto-generate from model changes**
```bash
# With Docker Compose
docker-compose exec backend alembic revision --autogenerate -m "add user roles"

# Without Docker Compose
cd backend && alembic revision --autogenerate -m "add user roles" && cd ..
```

This compares your models to the current schema and generates a migration file with detected changes.

**Manual migration (for complex changes Alembic can't detect)**
```bash
# With Docker Compose
docker-compose exec backend alembic revision -m "add custom function"

# Without Docker Compose
cd backend && alembic revision -m "add custom function" && cd ..
```

### Reviewing a Migration

Always review the generated migration file in `backend/alembic/versions/`:

```python
"""add user roles

Revision ID: a1b2c3d4
Revises: 9f8e7d6c
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'a1b2c3d4'
down_revision = '9f8e7d6c'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Apply migration."""
    op.add_column('users', sa.Column('role', sa.String(50), nullable=False, server_default='user'))

def downgrade() -> None:
    """Rollback migration."""
    op.drop_column('users', 'role')
```

**Check for issues:**
- Ensure `downgrade()` is the inverse of `upgrade()`
- Test both directions locally
- Review for data loss (e.g., dropping columns without backup)

### Running Migrations

Apply pending migrations to the database:

**Upgrade to latest schema**
```bash
# With Docker Compose
docker-compose exec backend alembic upgrade head

# Without Docker Compose
cd backend && alembic upgrade head && cd ..
```

**Upgrade by number**
```bash
# Apply next 3 migrations
docker-compose exec backend alembic upgrade +3
```

**Downgrade (rollback)**
```bash
# Rollback one migration
docker-compose exec backend alembic downgrade -1

# Rollback all migrations
docker-compose exec backend alembic downgrade base
```

## Common Tasks

### Check Current Schema Version

```bash
# With Docker Compose
docker-compose exec backend alembic current

# Without Docker Compose
cd backend && alembic current && cd ..
```

### View Migration History

```bash
# With Docker Compose
docker-compose exec backend alembic history

# Without Docker Compose
cd backend && alembic history && cd ..
```

### Test Migrations Locally

Before committing:

```bash
# Apply all migrations
docker-compose exec backend alembic upgrade head

# Verify schema with psql
docker-compose exec postgres psql -U postgres -d app_db -c "\dt"

# Rollback to test downgrade
docker-compose exec backend alembic downgrade -1

# Apply again
docker-compose exec backend alembic upgrade head
```

### Merge Conflicts in Migration Files

If two branches add conflicting migrations:

```bash
# View branches
docker-compose exec backend alembic branches

# Create a merge migration
docker-compose exec backend alembic merge -m "merge branches" <revision1> <revision2>
```

## Best Practices

1. **Auto-generate, then review** - Always check generated migrations for correctness
2. **Test both directions** - Verify `upgrade()` and `downgrade()` work
3. **Keep migrations small** - One logical change per migration
4. **Commit migration files** - Never skip committing `alembic/versions/` files
5. **Run before deployment** - Always test migrations in staging first
6. **Add data migrations carefully** - Use raw SQL for complex data transformations
7. **Avoid breaking changes** - Provide data migration path for column renames/drops

## Troubleshooting

### "No config file 'alembic.ini' found"

Alembic hasn't been initialized. Run:
```bash
docker-compose exec backend alembic init alembic
```

### "ModuleNotFoundError: No module named 'app'"

Ensure you're running from the backend directory or have proper Python path:
```bash
docker-compose exec backend alembic current  # Works (Docker has correct PYTHONPATH)
cd backend && alembic current  # Should also work
```

### Migration fails to auto-generate changes

Common causes:
- Import errors in `app/models/` - Check model syntax
- `target_metadata` not set in `env.py` - Verify config above
- Models not imported in `env.py` - Add `from app.models import Base`

### Accidental migration applied to production

Create a downgrade migration:
```bash
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic revision --autogenerate -m "fix incorrect migration"
docker-compose exec backend alembic upgrade head
```

## Integration with CI/CD

In your deployment pipeline:

```bash
# Run migrations on startup
docker-compose exec backend alembic upgrade head

# Application waits for schema to be ready
docker-compose up
```

Or in your Docker entrypoint script:

```bash
#!/bin/bash
# backend/entrypoint.sh
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy ORM Documentation](https://docs.sqlalchemy.org/en/20/orm/)
- [MyGym CLAUDE.md](../CLAUDE.md) - Development guidelines
