---
name: code-quality
description: Maintain code quality through linting, formatting, type checking, and pre-commit hooks
skills: [linting, formatting, testing, quality]
allowed-tools: [Bash, Read, Edit, Write]
---

# Code Quality Standards

Maintain consistent code quality across backend and frontend using automated tools.

## Backend Code Quality

### Setup Tools

**requirements-dev.txt**:
```
pytest==7.4.0
pytest-asyncio==0.21.0
pytest-cov==4.1.0
black==23.7.0
ruff==0.0.280
mypy==1.4.1
isort==5.12.0
```

### Linting with Ruff

```bash
# Check for issues
ruff check .

# Auto-fix simple issues
ruff check . --fix

# Check specific rule
ruff check . --select=E501  # Line too long
```

**pyproject.toml or ruff.toml**:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"
exclude = [".git", "__pycache__", "venv", ".venv"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "C",      # flake8-comprehensions
    "B",      # flake8-bugbear
]
ignore = ["E501"]  # Line too long (handled by formatter)
```

### Formatting with Black

```bash
# Format code
black .

# Check without modifying
black --check .

# Format specific file
black app/models/users.py
```

**pyproject.toml**:
```toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | venv
  | build
  | dist
)/
'''
```

### Type Checking with mypy

```bash
# Type check all code
mypy app/

# Check specific file
mypy app/models/users.py

# Strict mode
mypy app/ --strict
```

**pyproject.toml**:
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
strict_equality = true
ignore_missing_imports = false
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run only unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_users.py::test_create_user -v

# Run in watch mode
pytest-watch
```

**pytest.ini**:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (with database)
    asyncio: Async tests
```

### Pre-commit Hook Script

**scripts/quality-check.sh**:
```bash
#!/bin/bash
set -e

echo "🧹 Running code quality checks..."

echo "📝 Checking code formatting..."
ruff check . --fix || exit 1
black . || exit 1

echo "🔍 Type checking..."
mypy app/ || exit 1

echo "🧪 Running tests..."
pytest --cov=app --cov-report=term-missing || exit 1

echo "✅ All checks passed!"
```

**Setup pre-commit hook**:
```bash
# Make script executable
chmod +x scripts/quality-check.sh

# Create git hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
bash scripts/quality-check.sh
EOF

chmod +x .git/hooks/pre-commit
```

## Frontend Code Quality

### Setup Tools

**package.json**:
```json
{
  "devDependencies": {
    "typescript": "^5.1.0",
    "eslint": "^8.45.0",
    "eslint-plugin-react": "^7.32.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "prettier": "^3.0.0",
    "vitest": "^0.33.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.1.0",
    "jest-axe": "^8.0.0"
  }
}
```

### Type Checking

```bash
# Check TypeScript
npm run type-check

# Watch mode
tsc --watch
```

**.tsconfig.json**:
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### Linting with ESLint

```bash
# Check for issues
npm run lint

# Auto-fix
npm run lint -- --fix

# Check specific file
npm run lint -- src/components/UserForm.tsx
```

**.eslintrc.json**:
```json
{
  "extends": [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "parser": "@typescript-eslint/parser",
  "plugins": ["react", "react-hooks", "@typescript-eslint"],
  "rules": {
    "react/react-in-jsx-scope": "off",
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/explicit-function-return-types": "error",
    "@typescript-eslint/no-unused-vars": "error",
    "no-console": "warn"
  }
}
```

### Formatting with Prettier

```bash
# Format code
npm run format

# Check without modifying
npm run format -- --check

# Format specific file
npm run format -- src/components/UserForm.tsx
```

**.prettierrc**:
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always"
}
```

### Testing

```bash
# Run all tests
npm run test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run specific test file
npm run test -- UserForm.test.tsx

# Run tests matching pattern
npm run test -- --grep "should submit"
```

**vitest.config.ts**:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/tests/',
      ],
      lines: 80,
      functions: 80,
      branches: 80,
      statements: 80,
    },
  },
});
```

### Pre-commit Hook Script

**scripts/quality-check.sh** (frontend part):
```bash
#!/bin/bash
set -e

echo "🧹 Running frontend quality checks..."

echo "🔍 Type checking..."
npm run type-check || exit 1

echo "📝 Linting..."
npm run lint -- --fix || exit 1

echo "✨ Formatting..."
npm run format || exit 1

echo "🧪 Running tests..."
npm run test -- --run || exit 1

echo "✅ All frontend checks passed!"
```

## Continuous Integration (CI)

### GitHub Actions Example

**.github/workflows/quality.yml**:
```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linting
        run: ruff check .

      - name: Run type check
        run: mypy app/

      - name: Run tests
        run: pytest --cov=app

  frontend:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Type check
        run: npm run type-check

      - name: Lint
        run: npm run lint

      - name: Test
        run: npm run test -- --run
```

## Quality Metrics

### Coverage Targets

- **Backend**: >80% (unit + integration)
- **Frontend**: >75% (unit + integration)
- **Critical paths**: 100% (auth, payments, etc.)

### Code Review Checklist

- ✅ All tests pass
- ✅ Coverage maintained or improved
- ✅ No linting/formatting violations
- ✅ Types are strict (no `any`)
- ✅ No secrets in code
- ✅ Follows architectural patterns
- ✅ Documentation updated

### Pre-commit Check Script

```bash
#!/bin/bash
# Run before every git commit

echo "Running quality checks..."

# Backend
cd backend
bash ../scripts/quality-check.sh || exit 1
cd ..

# Frontend
cd frontend
bash ../scripts/quality-check.sh || exit 1
cd ..

echo "✅ Ready to commit!"
```

## IDE Configuration

### VS Code Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "charliermarsh.ruff",
    "ms-python.vscode-pylance",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "firsttris.vscode-jest-runner",
    "orta.vscode-jest"
  ]
}
```

### VS Code Settings

**.vscode/settings.json**:
```json
{
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[json]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```
