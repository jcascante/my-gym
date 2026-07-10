---
name: react-component-testing
description: Write React component tests using Vitest and React Testing Library with user-centric approach
skills: [vitest, testing-library, mocking]
allowed-tools: [Bash, Read, Edit, Write, TaskCreate]
---

# React Component Testing Skill

When writing React component tests, test **user behavior**, not implementation details.

## Test Structure

1. **Unit tests**: Individual component rendering and logic
2. **Integration tests**: Multiple components, data fetching flows
3. **Use MSW** (Mock Service Worker) for API mocking

## Example Pattern

```typescript
// src/tests/unit/UserForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import UserForm from '@/components/UserForm';

describe('UserForm', () => {
  it('should submit form with valid data', async () => {
    // Arrange
    const onSubmit = vi.fn();
    render(<UserForm onSubmit={onSubmit} />);

    // Act
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    const submitButton = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(submitButton);

    // Assert
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({ email: 'test@example.com' });
    });
  });

  it('should show error when form is invalid', async () => {
    render(<UserForm />);
    const submitButton = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(submitButton);

    expect(screen.getByText(/email is required/i)).toBeInTheDocument();
  });
});
```

## API Mocking with MSW

```typescript
// src/tests/setup.ts
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

export const server = setupServer(
  http.post('http://localhost:8000/api/v1/users', () => {
    return HttpResponse.json({ id: 1, email: 'test@example.com' });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## Best Practices

- Query by **role/label/text**, NOT by test-id (unless necessary)
- Use `screen` to query - it promotes accessible queries
- Test **user workflows**, not component state
- Mock API calls with MSW, don't make real requests
- Test error boundaries and loading states
- Use `waitFor` for async operations
- Test accessibility (a11y) with `jest-axe`

## Commands
- `npm run test:watch`: Run tests in watch mode
- `npm run test -- UserForm.test.tsx`: Run single file
- `npm run test:coverage`: Coverage report
