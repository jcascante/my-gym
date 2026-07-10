---
name: docker-workflows
description: Manage Docker and Docker Compose workflows for development, testing, and production builds
skills: [docker, docker-compose, containerization]
allowed-tools: [Bash, Read, Edit, Write]
---

# Docker Workflows Skill

Use Docker Compose for local development and Docker for production images. Backend and frontend deploy independently.

## Local Development with Docker Compose

### Starting Services

```bash
# Start all services (frontend, backend, postgres)
docker-compose up

# Start in background
docker-compose up -d

# Follow logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Accessing Services

```bash
# Backend shell
docker-compose exec backend bash
# Backend Python shell
docker-compose exec backend python

# Frontend shell
docker-compose exec frontend bash
# Frontend npm commands
docker-compose exec frontend npm test

# PostgreSQL shell
docker-compose exec postgres psql -U postgres -d app_db

# View all running services
docker-compose ps
```

### Database Operations in Container

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Seed database
docker-compose exec backend python -m scripts.seed_db
```

### Rebuilding After Changes

```bash
# Rebuild images if dependencies changed
docker-compose build

# Rebuild specific service
docker-compose build backend

# Rebuild without cache
docker-compose build --no-cache

# Rebuild and restart
docker-compose up -d --build
```

## Development Dockerfile Structure

### Backend (Dockerfile)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Run migrations and start server
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0"]
```

### Frontend (Dockerfile)
```dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy code
COPY . .

# Run dev server
CMD ["npm", "run", "dev", "--", "--host"]
```

## Production Docker Images

### Building Production Images

```bash
# Backend production build
docker build -f backend/Dockerfile.prod \
  -t myregistry/my-gym-backend:1.0.0 \
  ./backend

# Frontend production build
docker build -f frontend/Dockerfile.prod \
  -t myregistry/my-gym-frontend:1.0.0 \
  ./frontend

# Tag for registry
docker tag amy-gym-backend:1.0.0 myregistry/my-gym-backend:latest
```

### Production Dockerfile Examples

**Backend (Dockerfile.prod)** - Multi-stage build:
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH

# Run migrations and start with gunicorn
CMD ["bash", "-c", "alembic upgrade head && gunicorn -w 4 -b 0.0.0.0:8000 app.main:app"]
```

**Frontend (Dockerfile.prod)** - Nginx serving:
```dockerfile
# Build stage
FROM node:20-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

## Docker Compose Configuration

**docker-compose.yml** structure:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/app_db
      SQLALCHEMY_DATABASE_URL: postgresql://postgres:postgres@postgres:5432/app_db
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      VITE_API_URL: http://localhost:8000
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app

volumes:
  postgres_data:
```

## Testing in Docker

```bash
# Run backend tests in container
docker-compose exec backend pytest

# Run frontend tests in container
docker-compose exec frontend npm test

# With coverage
docker-compose exec backend pytest --cov=app

# Single test file
docker-compose exec backend pytest tests/integration/test_users.py -v
```

## Cleanup

```bash
# Stop containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove volumes (careful - removes data!)
docker-compose down -v

# Remove unused images/volumes system-wide
docker system prune -a
```

## Deployment Steps

1. **Build production images** with version tags
2. **Push to registry** (Docker Hub, ECR, etc.)
3. **Deploy backend** to backend host/service
4. **Run migrations** on new deployment
5. **Deploy frontend** to frontend host/CDN
6. **Verify both services** are up and communicating
