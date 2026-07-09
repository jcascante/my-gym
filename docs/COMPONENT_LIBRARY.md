# MyGym Component Library

Professional, accessible, responsive React components built with TypeScript and Tailwind CSS.

## Core Components

### Button

Flexible button component with variants, sizes, and loading states.

```typescript
import { Button } from '@/components'

<Button variant="primary" size="md" isLoading={false}>
  Click me
</Button>
```

**Props:**
- `variant`: 'primary' | 'secondary' | 'danger' (default: 'primary')
- `size`: 'sm' | 'md' | 'lg' (default: 'md')
- `isLoading`: boolean (default: false)
- `disabled`: boolean
- Standard HTMLButtonElement props

**Accessibility:**
- Semantic button element
- Focus-visible outline styles
- Loading spinner with aria support
- Disabled state prevents clicks

---

### FormField

Form input wrapper with label, error message, and hints.

```typescript
import { FormField } from '@/components'

<FormField
  label="Email"
  type="email"
  error={errors.email}
  hint="We'll never share your email"
  required
/>
```

**Props:**
- `label`: string - Field label
- `error`: string - Error message (shows when provided)
- `hint`: string - Helper text below input
- `required`: boolean - Adds asterisk to label
- Standard HTMLInputElement props

**Accessibility:**
- Associated label with htmlFor
- ARIA-compliant error display
- Focus ring on input
- Disabled state styling

---

### Card

Container component for grouping content with consistent styling.

```typescript
import { Card } from '@/components'

<Card padding="md">
  <h2>Card Title</h2>
  <p>Card content</p>
</Card>
```

**Props:**
- `padding`: 'sm' | 'md' | 'lg' (default: 'md')
- Standard HTMLDivElement props

---

### Alert

Dismissible alert component with multiple types.

```typescript
import { Alert } from '@/components'

<Alert type="success" title="Success!" dismissible onDismiss={() => setAlert(null)}>
  Your changes have been saved.
</Alert>
```

**Types:** 'success' | 'error' | 'warning' | 'info'

**Props:**
- `type`: Alert type (default: 'info')
- `title`: Optional title
- `dismissible`: boolean (default: false)
- `onDismiss`: Callback when dismissed
- Standard HTMLDivElement props

**Accessibility:**
- role="alert" for screen readers
- Icon for visual context
- Focus-visible dismiss button

---

### Spinner

Loading indicator with optional fullscreen overlay.

```typescript
import { Spinner } from '@/components'

// Inline spinner
<Spinner size="md" />

// Fullscreen loading overlay
<Spinner fullscreen />
```

**Props:**
- `size`: 'sm' | 'md' | 'lg' (default: 'md')
- `fullscreen`: boolean (default: false)

---

## Custom Hooks

### useResponsive

Detect if viewport is at least a specific breakpoint.

```typescript
import { useResponsive } from '@/hooks/useResponsive'

const isMobile = useResponsive('sm')
const isTablet = useResponsive('md')
const isDesktop = useResponsive('lg')
```

### useBreakpoint

Get current breakpoint name.

```typescript
import { useBreakpoint } from '@/hooks/useResponsive'

const breakpoint = useBreakpoint() // 'sm' | 'md' | 'lg' | 'xl' | '2xl'
```

### useResponsiveValue

Provide different values per breakpoint.

```typescript
import { useResponsiveValue } from '@/hooks/useResponsive'

const textSize = useResponsiveValue({
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
})
```

---

## Component Patterns

### Form Submission

```typescript
import { Button, FormField, Alert } from '@/components'

export const LoginForm = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // API call
      await loginAPI(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <Alert type="error" dismissible>{error}</Alert>}
      <FormField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <FormField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <Button type="submit" isLoading={loading} className="w-full">
        Sign in
      </Button>
    </form>
  )
}
```

### Responsive Grid

```typescript
// Mobile: 1 column, Tablet: 2 columns, Desktop: 3 columns
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map((item) => (
    <Card key={item.id}>{item.name}</Card>
  ))}
</div>
```

### Conditional Rendering by Breakpoint

```typescript
import { useResponsive } from '@/hooks/useResponsive'

export const ResponsiveNav = () => {
  const isMobile = useResponsive('sm')

  return isMobile ? <MobileNav /> : <DesktopNav />
}
```

### Loading and Error States

```typescript
import { Spinner, Alert } from '@/components'

export const DataDisplay = () => {
  const { data, isLoading, error } = useQuery()

  if (isLoading) return <Spinner fullscreen />
  if (error) return <Alert type="error">{error.message}</Alert>

  return <div>{/* content */}</div>
}
```

---

## Styling Best Practices

### Use Tailwind Classes

```typescript
// ✅ Good: Use Tailwind utilities
<div className="flex items-center gap-4 p-4 rounded-lg bg-primary-100">
  <p className="text-sm font-medium text-primary-900">Badge</p>
</div>

// ❌ Avoid: Inline styles
<div style={{ display: 'flex', alignItems: 'center', padding: '16px' }}>
  ...
</div>
```

### Responsive Classes

```typescript
// ✅ Mobile-first approach
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
  ...
</div>

// ✅ Responsive spacing
<button className="px-3 py-2 sm:px-4 sm:py-3 text-sm sm:text-base">
  Touch-friendly button
</button>
```

### Dark Mode

```typescript
// ✅ Explicit dark mode support
<div className="bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white">
  Content adapts to theme
</div>
```

### Accessibility Classes

```typescript
// ✅ Focus visible styles (auto-applied to buttons, links, inputs)
// ✅ Skip links for keyboard nav
// ✅ ARIA labels on icon buttons
<button aria-label="Close menu">
  <CloseIcon />
</button>
```

---

## Common Mistakes to Avoid

### ❌ Don't mix styling approaches

```typescript
// Bad: Mix inline, CSS, and Tailwind
<div style={{ padding: '10px' }} className="flex gap-4">
  ...
</div>
```

### ✅ Do use Tailwind consistently

```typescript
// Good: Pure Tailwind
<div className="flex gap-4 p-2.5">
  ...
</div>
```

### ❌ Don't hardcode colors

```typescript
// Bad: Hardcoded color values
<div style={{ backgroundColor: '#ff0000' }}>Error</div>
```

### ✅ Do use design tokens

```typescript
// Good: Use theme colors
<Alert type="error">Error message</Alert>
```

### ❌ Don't ignore mobile

```typescript
// Bad: Only designed for desktop
<button className="px-6 py-4 text-lg">Submit</button>
```

### ✅ Do design mobile-first

```typescript
// Good: Touch-friendly on all devices
<button className="px-4 py-3 sm:px-6 sm:py-4 text-base sm:text-lg">Submit</button>
```

---

## Testing Components

### Unit Test Template

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '../Button'

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
  })

  it('fires onClick handler', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click</Button>)
    await user.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalled()
  })

  it('shows loading state', () => {
    render(<Button isLoading>Submit</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('respects disabled prop', () => {
    render(<Button disabled>Disabled</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})
```

---

## Performance Tips

1. **Lazy load components** at route level
2. **Memoize expensive components** (Card lists, Form sections)
3. **Use React Query** for data fetching with automatic caching
4. **Code split** by route
5. **Optimize images** before adding to components

---

## Resources

- [Tailwind CSS Docs](https://tailwindcss.com/)
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [WAI-ARIA Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Testing Library Docs](https://testing-library.com/react)
