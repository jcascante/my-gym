# MyGym Documentation

Welcome to the MyGym documentation hub. Start with [index.html](index.html) for the user guide, or use the links below for technical docs and additional resources.

## 📚 Documentation Structure

**All documentation is published as HTML via GitHub Pages** for professional presentation and optimal styling.

**Main page**: [index.html](index.html) — User-focused guide with feature overview

### User Documentation
**For end users who want to use MyGym**  
**Format: HTML** — Styled with friendly colors, emoji headers, and interactive elements

- **[Login & Sign-Up Guide](user/LOGIN_SIGNUP.html)** — How to create an account, log in, and manage your account securely
  - Account creation
  - Login process
  - Logout functionality
  - Password security
  - Account recovery

### Technical Documentation
**For developers and system administrators**  
**Format: HTML** — Syntax-highlighted code blocks, navigation sidebar, flow diagrams

- **[Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.html)** — Deep dive into JWT auth, password hashing, and session management
  - JWT token implementation
  - Password hashing with SHA-256 + bcrypt
  - API endpoints (sign-up, login, logout, refresh)
  - Frontend/backend architecture
  - Testing strategies
  - Deployment considerations

### Shared Reference Documentation
**For all audiences**  
**Format: Markdown** — For longer reference docs (migrations, setup guides)

- **[Database Migrations Guide](DATABASE_MIGRATIONS.md)** — Using Alembic for database schema versioning
  - Migration workflow
  - Creating migrations
  - Testing up/down migrations
  - Best practices

- **[UV Package Manager Setup](UV_SETUP.md)** — Dependency management with uv
  - Installation
  - Configuration
  - Common commands
  - Dependency resolution

### Personal Notes
**Project-specific context and decisions**

See the `personal/` directory for development notes, architectural decisions, and project context.

---

## 🚀 Quick Start by Role

### I'm a new user
1. Start with [Login & Sign-Up Guide](user/LOGIN_SIGNUP.md)
2. Create your account
3. Set up your fitness profile

### I'm a developer
1. Read [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.md) to understand the auth system
2. Check [Database Migrations Guide](DATABASE_MIGRATIONS.md) for schema management
3. See [UV Setup Guide](UV_SETUP.md) for dependency management
4. Review the main [README.md](../README.md) for development commands

### I'm a DevOps/Infrastructure engineer
1. Check [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.md) for deployment considerations
2. Review [Database Migrations Guide](DATABASE_MIGRATIONS.md) for production migrations
3. See the main [README.md](../README.md) for Docker and deployment commands

### I'm reviewing code
1. [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.md) covers implementation patterns
2. [Database Migrations Guide](DATABASE_MIGRATIONS.md) documents schema changes
3. Check personal notes for architectural decisions

---

## 📖 Full Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| [Login & Sign-Up Guide](user/LOGIN_SIGNUP.html) | User-friendly authentication guide | End users |
| [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.html) | Implementation details and architecture | Developers |
| [Database Migrations Guide](DATABASE_MIGRATIONS.md) | Schema versioning with Alembic | DevOps, Developers |
| [UV Setup Guide](UV_SETUP.md) | Package manager configuration | Developers |
| [README.md](../README.md) | Project overview and quick start | Everyone |

---

## 🔍 Finding What You Need

**Login or authentication questions?**
- User: [Login & Sign-Up Guide](user/LOGIN_SIGNUP.md)
- Developer: [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.md)

**Database or schema questions?**
- [Database Migrations Guide](DATABASE_MIGRATIONS.md)

**Dependency or setup issues?**
- [UV Setup Guide](UV_SETUP.md)

**Getting started with development?**
- [README.md](../README.md) — Quick start and commands

---

## 📋 MyGym Overview

MyGym is a personalized workout program manager that:

- ✅ Creates custom workout programs based on user goals and fitness level
- ✅ Tracks daily workouts with detailed logging
- ✅ Provides performance analytics and progress tracking
- ✅ Collects user feedback to adapt programs

**Tech Stack:**
- Backend: FastAPI, SQLAlchemy, Pydantic
- Frontend: React 19, TypeScript, Zustand
- Database: PostgreSQL (prod), SQLite (testing)
- Package Manager: uv
- Quality: Ruff, Black, mypy, ESLint, Prettier

---

## 🔗 Navigation

- [← Back to Main README](../README.md)
- [User Documentation](user/index.html)
- [Technical Documentation](technical/index.html)
- [Personal Notes](personal/)

---

## 💡 Contributing Documentation

When adding new documentation:

1. **User docs** go in `docs/user/` with clear, non-technical language
2. **Technical docs** go in `docs/technical/` with implementation details
3. **Personal notes** go in `docs/personal/` for project-specific context
4. Update relevant index.html files and this README.md with links

---

Last updated: 2026-07-09
