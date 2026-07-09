#!/bin/bash
# Initialize database with Alembic migrations
# Usage: ./scripts/init-db.sh [with-docker|without-docker]

set -e

MODE="${1:-with-docker}"

echo "🗂️  Initializing database for MyGym..."

if [ "$MODE" = "with-docker" ] || [ "$MODE" = "" ]; then
    echo "📦 Using Docker Compose"

    # Check if alembic directory exists
    if [ ! -d "backend/alembic" ]; then
        echo "🔧 Initializing Alembic..."
        docker-compose exec -T backend alembic init alembic
        echo "✅ Alembic initialized"
    else
        echo "ℹ️  Alembic already initialized"
    fi

    # Create initial migration if none exist
    MIGRATION_COUNT=$(find backend/alembic/versions -name "*.py" 2>/dev/null | wc -l || echo 0)
    if [ "$MIGRATION_COUNT" -eq 0 ]; then
        echo "🔄 Creating initial migration..."
        docker-compose exec -T backend alembic revision --autogenerate -m "initial schema"
        echo "✅ Initial migration created"
    else
        echo "ℹ️  Migrations already exist ($MIGRATION_COUNT found)"
    fi

    # Run migrations
    echo "🚀 Running migrations..."
    docker-compose exec -T backend alembic upgrade head
    echo "✅ Database schema updated"

    # Verify
    echo "🔍 Checking migration status..."
    docker-compose exec -T backend alembic current
    echo "✅ Database initialization complete!"

elif [ "$MODE" = "without-docker" ]; then
    echo "🖥️  Running locally (without Docker)"

    cd backend || exit 1

    # Check Python and alembic
    if ! command -v alembic &> /dev/null; then
        echo "❌ Alembic not installed. Run: pip install alembic sqlalchemy"
        exit 1
    fi

    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        echo "❌ Python not installed"
        exit 1
    fi

    # Check if alembic directory exists
    if [ ! -d "alembic" ]; then
        echo "🔧 Initializing Alembic..."
        alembic init alembic
        echo "✅ Alembic initialized"
    else
        echo "ℹ️  Alembic already initialized"
    fi

    # Create initial migration if none exist
    MIGRATION_COUNT=$(find alembic/versions -name "*.py" 2>/dev/null | wc -l || echo 0)
    if [ "$MIGRATION_COUNT" -eq 0 ]; then
        echo "🔄 Creating initial migration..."
        alembic revision --autogenerate -m "initial schema"
        echo "✅ Initial migration created"
    else
        echo "ℹ️  Migrations already exist ($MIGRATION_COUNT found)"
    fi

    # Run migrations
    echo "🚀 Running migrations..."
    alembic upgrade head
    echo "✅ Database schema updated"

    # Verify
    echo "🔍 Checking migration status..."
    alembic current
    echo "✅ Database initialization complete!"

    cd ..
else
    echo "❌ Unknown mode: $MODE"
    echo "Usage: $0 [with-docker|without-docker]"
    exit 1
fi
