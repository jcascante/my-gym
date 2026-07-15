# MyGym Documentation

Welcome to the MyGym documentation hub. Start with [index.html](index.html) for the user guide, or use the links below for technical docs and additional resources.

## 📚 Documentation Structure

**All documentation is published as HTML via GitHub Pages** for professional presentation and optimal styling.

**Main page**: [index.html](index.html) — User-focused guide with feature overview

### User Documentation
**For end users who want to use MyGym**
**Format: HTML** — Styled with friendly colors, emoji headers, and interactive elements

- **[Login & Sign-Up Guide](user/LOGIN_SIGNUP.html)** — How to create an account, log in, and manage your account securely
  - Account creation (with password confirmation)
  - Login process
  - Password visibility toggle
  - Logout functionality
  - Password security
  - Account recovery

- **[Getting Started / Onboarding Guide](user/ONBOARDING.html)** — The 6-step onboarding wizard new users complete on first login
  - Personal Information, Fitness Level, Workout Preferences, Training Environments, Goals, Additional Information steps
  - Progress bar and Back/Next navigation
  - What returning users see instead

- **[Training Environments Guide](user/TRAINING_ENVIRONMENTS.html)** — Saving the different places you train and their equipment
  - Adding, editing, and deleting environments
  - Setting a default environment
  - The program-creation preferences questionnaire (placeholder)

### Technical Documentation
**For developers and system administrators**
**Format: HTML** — Syntax-highlighted code blocks, navigation sidebar, flow diagrams

- **[Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.html)** — Deep dive into JWT auth, password hashing, and session management
  - JWT token implementation
  - Password hashing with SHA-256 + bcrypt
  - Client-side password confirmation and the password visibility toggle
  - API endpoints (sign-up, login, logout, refresh)
  - Frontend/backend architecture
  - Testing strategies
  - Deployment considerations

- **[Onboarding Flow Technical Reference](technical/ONBOARDING_FLOW_TECHNICAL.html)** — Profile-gated routing and the multi-step onboarding wizard
  - Conditional routing (profile null vs. exists)
  - Multi-step wizard state management and per-step validation
  - API endpoints and data models

- **[Training Environments & Program Creation Technical Reference](technical/TRAINING_ENVIRONMENTS_TECHNICAL.html)** — Multi-environment data model, CRUD API, and the program-generation request placeholder
  - `TrainingEnvironment` model, migration, and default-exclusivity enforcement
  - CRUD endpoints and the `POST /programs` 501 placeholder
  - Frontend components, pages, and the onboarding Save/Next UX fix

- **[Infrastructure & Deployment Technical Reference](technical/INFRASTRUCTURE_DEPLOYMENT_TECHNICAL.html)** — Terraform-managed AWS infrastructure and the GitHub Actions deploy pipeline
  - Terraform modules: ECR, IAM/OIDC, ECS Fargate, RDS
  - GitHub Actions workflow: backend and frontend deploy jobs
  - OIDC-based AWS authentication (no stored credentials)
  - Database migration strategy in CI

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
1. Start with [Login & Sign-Up Guide](user/LOGIN_SIGNUP.html)
2. Create your account
3. Complete the [onboarding wizard](user/ONBOARDING.html) to set up your fitness profile

### I'm a developer
1. Read [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.html) to understand the auth system
2. Read [Onboarding Flow Technical Reference](technical/ONBOARDING_FLOW_TECHNICAL.html) for the conditional routing and wizard implementation
3. Check [Database Migrations Guide](DATABASE_MIGRATIONS.md) for schema management
4. See [UV Setup Guide](UV_SETUP.md) for dependency management
5. Review the main [README.md](../README.md) for development commands

### I'm a DevOps/Infrastructure engineer
1. Start with [Infrastructure & Deployment Technical Reference](technical/INFRASTRUCTURE_DEPLOYMENT_TECHNICAL.html) for Terraform modules and the GitHub Actions pipeline
2. Check [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.html) for auth-related deployment considerations
3. Review [Database Migrations Guide](DATABASE_MIGRATIONS.md) for how migrations run in CI
4. See the main [README.md](../README.md) for Docker and deployment commands

### I'm reviewing code
1. [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.md) covers implementation patterns
2. [Database Migrations Guide](DATABASE_MIGRATIONS.md) documents schema changes
3. Check personal notes for architectural decisions

---

## 📖 Full Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| [Login & Sign-Up Guide](user/LOGIN_SIGNUP.html) | User-friendly authentication guide | End users |
| [Onboarding Guide](user/ONBOARDING.html) | The 6-step onboarding wizard | End users |
| [Training Environments Guide](user/TRAINING_ENVIRONMENTS.html) | Saving training locations and equipment | End users |
| [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.html) | Implementation details and architecture | Developers |
| [Onboarding Flow Technical Reference](technical/ONBOARDING_FLOW_TECHNICAL.html) | Conditional routing and wizard implementation | Developers |
| [Training Environments & Program Creation Technical Reference](technical/TRAINING_ENVIRONMENTS_TECHNICAL.html) | Multi-environment data model, CRUD API, and program creation placeholder | Developers |
| [Infrastructure & Deployment Technical Reference](technical/INFRASTRUCTURE_DEPLOYMENT_TECHNICAL.html) | Terraform modules and the GitHub Actions deploy pipeline | DevOps, Developers |
| [Database Migrations Guide](DATABASE_MIGRATIONS.md) | Schema versioning with Alembic | DevOps, Developers |
| [UV Setup Guide](UV_SETUP.md) | Package manager configuration | Developers |
| [README.md](../README.md) | Project overview and quick start | Everyone |

---

## 🔍 Finding What You Need

**Login or authentication questions?**
- User: [Login & Sign-Up Guide](user/LOGIN_SIGNUP.html)
- Developer: [Authentication Technical Reference](technical/LOGIN_SIGNUP_TECHNICAL.html)

**Onboarding questions?**
- User: [Onboarding Guide](user/ONBOARDING.html)
- Developer: [Onboarding Flow Technical Reference](technical/ONBOARDING_FLOW_TECHNICAL.html)

**Training environments or program creation questions?**
- User: [Training Environments Guide](user/TRAINING_ENVIRONMENTS.html)
- Developer: [Training Environments & Program Creation Technical Reference](technical/TRAINING_ENVIRONMENTS_TECHNICAL.html)

**Infrastructure or deployment questions?**
- [Infrastructure & Deployment Technical Reference](technical/INFRASTRUCTURE_DEPLOYMENT_TECHNICAL.html)

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

Last updated: 2026-07-15
