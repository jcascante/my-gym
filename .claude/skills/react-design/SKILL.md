---
name: react-design
description: Frontend design system with responsive patterns, accessibility, component structure, and styling guidelines
skills: [design, frontend, react, typescript, responsive, accessibility]
allowed-tools: [Read, Edit, Write]
---

# React + TypeScript Frontend Design Guide

MyGym frontend follows professional design practices for desktop, tablet, and mobile (iOS/Android). This guide ensures consistency, accessibility, performance, and maintainability.

## Design System Principles

- **Mobile-First**: Build for mobile, enhance for larger screens
- **Type-Safe**: Leverage TypeScript for component props and state
- **Accessible**: WCAG 2.1 AA minimum (semantic HTML, keyboard nav, screen readers)
- **Responsive**: Single codebase serves desktop, tablet, mobile
- **Performance**: Lazy load, code split, optimize images
- **Reusable**: DRY components, composition over inheritance
- **Testable**: Every component has unit + visual tests

## Design Tokens (Theme)

Located in `src/styles/theme.ts`:

```typescript
export const theme = {
  colors: {
    primary: '#2563eb',      // Navy blue
    secondary: '#7c3aed',    // Purple
    success: '#10b981',      // Green
    warning: '#f59e0b',      // Amber
    error: '#ef4444',        // Red
    neutral: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      300: '#d1d5db',
      400: '#9ca3af',
      500: '#6b7280',
      600: '#4b5563',
      700: '#374151',
      800: '#1f2937',
      900: '#111827',
    },
  },
  spacing: {
    xs: '0.25rem',  // 4px
    sm: '0.5rem',   // 8px
    md: '1rem',     // 16px
    lg: '1.5rem',   // 24px
    xl: '2rem',     // 32px
    '2xl': '3rem',  // 48px
  },
  typography: {
    fontFamily: {
      system: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    },
    fontSize: {
      xs: '0.75rem',      // 12px
      sm: '0.875rem',     // 14px
      base: '1rem',       // 16px
      lg: '1.125rem',     // 18px
      xl: '1.25rem',      // 20px
      '2xl': '1.5rem',    // 24px
      '3xl': '1.875rem',  // 30px
      '4xl': '2.25rem',   // 36px
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.75,
    },
  },
  borderRadius: {
    sm: '0.25rem',   // 4px
    md: '0.5rem',    // 8px
    lg: '0.75rem',   // 12px
    xl: '1rem',      // 16px
    full: '9999px',
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
  },
  breakpoints: {
    sm: '640px',    // Mobile
    md: '768px',    // Tablet
    lg: '1024px',   // Desktop
    xl: '1280px',   // Wide desktop
  },
}
```

## Responsive Design Patterns

### Mobile-First Approach

```typescript
// Use Tailwind's responsive prefixes: sm:, md:, lg:, xl:
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Single column on mobile, 2 on tablets, 3 on desktop */}
</div>
```

### Touch-Friendly Sizing

- Minimum touch target: 44x44px (mobile)
- Minimum spacing between targets: 8px
- Font size: min 16px on mobile (prevents auto zoom)

```typescript
<button className="px-4 py-3 sm:px-6 sm:py-4 text-base sm:text-lg">
  Touch-friendly button
</button>
```

## Component Structure

### Base Component Pattern

```typescript
// src/components/Button.tsx
import { FC, ButtonHTMLAttributes } from 'react'
import styles from './Button.module.css'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  children: React.ReactNode
}

export const Button: FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  children,
  ...props
}) => {
  return (
    <button
      className={`${styles.button} ${styles[variant]} ${styles[size]}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? 'Loading...' : children}
    </button>
  )
}
```

## Accessibility (A11y) Guidelines

### Semantic HTML

```typescript
// ❌ Bad: Using div for everything
<div onClick={handleClick}>Submit</div>

// ✅ Good: Use semantic elements
<button type="submit">Submit</button>
```

### ARIA Labels

```typescript
// For icon-only buttons
<button aria-label="Close menu" className="p-2">
  <CloseIcon />
</button>

// For screen readers
<img src="user.jpg" alt="User profile photo" />
```

### Color Contrast

- Text: Minimum 4.5:1 ratio (AA)
- Large text (18px+): Minimum 3:1 ratio
- Use design tokens; never hardcode unsafe colors

## Dark Mode Support

Design for light AND dark modes. Tailwind's `dark:` prefix:

```typescript
<div className="bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white">
  Content adapts to system preference
</div>
```

## States & Feedback

### Loading State

```typescript
<button disabled={isLoading}>
  {isLoading ? (
    <>
      <Spinner className="inline mr-2" /> Loading...
    </>
  ) : (
    'Submit'
  )}
</button>
```

### Error State

```typescript
{error && (
  <div role="alert" className="bg-error-50 border-l-4 border-error p-4">
    <p className="text-error font-semibold">{error}</p>
  </div>
)}
```

## Performance Optimization

### Code Splitting

```typescript
const LoginPage = lazy(() => import('@/pages/LoginPage'))
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))

<Suspense fallback={<LoadingSpinner />}>
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/dashboard" element={<DashboardPage />} />
  </Routes>
</Suspense>
```

### Memoization

```typescript
const UserCard = memo(({ userId }: { userId: number }) => (
  <div>{userId}</div>
), (prev, next) => prev.userId === next.userId)
```

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge latest)
- iOS 13+, Android 5+
- Graceful degradation for older browsers
