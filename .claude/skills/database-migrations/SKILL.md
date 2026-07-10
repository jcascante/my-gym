---
name: database-migrations
description: Manage database schema changes safely with Alembic migrations and version control
skills: [alembic, sqlalchemy, migrations]
allowed-tools: [Bash, Read, Edit, Write]
---

# Database Migrations Skill

All schema changes must go through Alembic migrations. Never modify the database directly.

## Migration Workflow

### Creating a Migration

1. **Make model changes** in `app/models/`
2. **Auto-generate migration**:
   ```bash
   alembic revision --autogenerate -m "add_email_column_to_users"
   ```
3. **Review the generated file** in `migrations/versions/` - DO NOT TRUST auto-generate blindly
4. **Test locally**:
   ```bash
   alembic upgrade head      # Apply migration
   alembic downgrade -1      # Rollback to verify
   alembic upgrade head      # Re-apply
   ```
5. **Commit to version control** (the .py file, never .sql)

## Example Migration File

```python
# migrations/versions/002_add_email_column.py
"""add email column to users table

Revision ID: abc123def456
Revises: 001_initial
Create Date: 2024-01-15 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123def456'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # Backward compatible: add column as nullable first
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    
def downgrade():
    op.drop_constraint('uq_users_email', 'users')
    op.drop_column('users', 'email')
```

## Data Migrations

For data changes (not just schema):

```python
def upgrade():
    # Add new column
    op.add_column('users', sa.Column('full_name', sa.String(255)))
    
    # Migrate existing data
    connection = op.get_bind()
    connection.execute("""
        UPDATE users 
        SET full_name = first_name || ' ' || last_name
        WHERE first_name IS NOT NULL
    """)

def downgrade():
    op.drop_column('users', 'full_name')
```

## Common Commands

```bash
alembic current                    # Show current revision
alembic history                    # Show all revisions
alembic upgrade head               # Apply all pending migrations
alembic upgrade +2                 # Apply next 2 migrations
alembic downgrade -1               # Rollback one migration
alembic downgrade base             # Rollback everything
alembic heads                       # Show head revisions (if branched)
```

## Best Practices

1. **One logical change per migration** - easier to debug/rollback
2. **Make migrations backward compatible** - nullable columns first, then backfill
3. **Test up AND down** - ensure rollbacks work
4. **Use descriptive names** - `add_email_to_users` not `update_schema`
5. **Never hardcode IDs** - use relationships and constraints
6. **Set constraints carefully** - can block production deploys
7. **Index frequently queried columns** - but only when needed (perf impact on INSERT)
8. **Document complex migrations** - add comments explaining the why

## Testing Migrations

In Docker Compose:
```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head
```

## Deployment Checklist

Before deploying a migration:
- [ ] Run migrate locally (upgrade + downgrade)
- [ ] Run tests with migration applied
- [ ] Check data integrity after migration
- [ ] Plan rollback strategy if needed
- [ ] Notify team about migration timing (might lock tables)
