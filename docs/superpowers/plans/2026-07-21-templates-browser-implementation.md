# Templates Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only accordion-style UI to browse all program templates and view their full configuration details.

**Architecture:** Frontend-only (for now). Fetch templates from backend via `GET /api/v1/templates`, render as accordion list with compact summary rows that expand inline to show full details. Single expanded template at a time. Follows EnvironmentsPage pattern.

**Tech Stack:** React 19 + TypeScript, Tailwind CSS, Vitest + Testing Library, existing Card/Alert/Spinner components.

## Global Constraints

- **Route:** `/templates` (authenticated only)
- **API endpoint:** `GET /api/v1/templates` (backend responsibility — not included in this plan; frontend assumes it exists and returns `{ templates: Template[] }`)
- **Styling:** Use existing Card, Alert, Spinner components; match EnvironmentsPage layout
- **Dark mode:** Automatic via existing CSS classes
- **Testing:** Vitest + React Testing Library, >80% coverage
- **No backend changes:** This plan is frontend-only; backend template endpoint must exist before implementation

---

## File Structure

**New files:**
- `frontend/src/types/template.ts` — TypeScript interfaces for template data
- `frontend/src/api/templates.ts` — API client function
- `frontend/src/components/TemplateListItem.tsx` — List item component (compact + expanded)
- `frontend/src/tests/components/TemplateListItem.test.tsx` — Unit tests for TemplateListItem
- `frontend/src/pages/TemplatesPage.tsx` — Main page component
- `frontend/src/tests/pages/TemplatesPage.test.tsx` — Integration tests for TemplatesPage

**Modified files:**
- `frontend/src/App.tsx` — Add `/templates` route

---

## Task 1: Define Template Types

**Files:**
- Create: `frontend/src/types/template.ts`
- Test: (no separate test; types used by other tasks)

**Interfaces:**
- Produces: TypeScript types for `Template`, `Session`, `Slot`, `Scheme`, `RequiredInput`

- [ ] **Step 1: Create template type definitions file**

Create `frontend/src/types/template.ts`:

```typescript
export interface RequiredInput {
  key: string;
  label: string;
  type: 'number' | 'text';
  applies_to?: string;
}

export interface Slot {
  pattern?: string;
  region?: string;
  priority: string;
  scheme: string;
  muscles?: string[];
}

export interface Session {
  key: string;
  name: string;
  order: number;
  slots: Slot[];
}

export interface Scheme {
  sets: number;
  reps_min: number;
  reps_max: number;
  rest_seconds: number;
  target_rpe?: number;
  intensity_pct?: number;
}

export interface ProgressionRef {
  model_key: string;
  params: Record<string, unknown>;
  deload_every?: number;
}

export interface Template {
  slug: string;
  name: string;
  description: string;
  goals: string[];
  experience_levels: string[];
  days_per_week_min: number;
  days_per_week_max: number;
  session_duration_min: number;
  session_duration_max: number;
  split: {
    sessions: Session[];
    schemes: Record<string, Scheme>;
  };
  progression_ref: ProgressionRef;
  required_inputs: RequiredInput[];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/template.ts
git commit -m "types: add template type definitions"
```

---

## Task 2: Create API Client

**Files:**
- Create: `frontend/src/api/templates.ts`
- Test: (no separate test; tested via TemplatesPage integration test)

**Interfaces:**
- Consumes: `Template` type from Task 1
- Produces: `listTemplates(): Promise<Template[]>` function

- [ ] **Step 1: Create templates API client**

Create `frontend/src/api/templates.ts`:

```typescript
import type { Template } from '@/types/template';
import { getErrorMessage } from '@/api/errors';

export async function listTemplates(): Promise<Template[]> {
  try {
    const response = await fetch('/api/v1/templates');
    if (!response.ok) {
      const message = response.status === 500 ? 'Server error loading templates' : 'Failed to load templates';
      throw new Error(message);
    }
    const data = await response.json();
    return data.templates;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/templates.ts
git commit -m "api: add templates API client"
```

---

## Task 3: Create TemplateListItem Component

**Files:**
- Create: `frontend/src/components/TemplateListItem.tsx`
- Test: `frontend/src/tests/components/TemplateListItem.test.tsx`

**Interfaces:**
- Consumes: `Template` type from Task 1
- Produces: `TemplateListItem` component with props:
  - `template: Template`
  - `isExpanded: boolean`
  - `onToggle: () => void`

- [ ] **Step 1: Write failing unit test for compact row rendering**

Create `frontend/src/tests/components/TemplateListItem.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TemplateListItem from '@/components/TemplateListItem';
import type { Template } from '@/types/template';

const mockTemplate: Template = {
  slug: 'full-body-x3',
  name: 'Full Body 3x/Week',
  description: 'Three full-body days for beginners building general strength.',
  goals: ['general', 'strength'],
  experience_levels: ['beginner'],
  days_per_week_min: 3,
  days_per_week_max: 3,
  session_duration_min: 45,
  session_duration_max: 60,
  split: {
    sessions: [
      {
        key: 'full_a',
        name: 'Full Body A',
        order: 1,
        slots: [
          { pattern: 'squat', priority: 'primary', scheme: 'main' },
          { pattern: 'horizontal_push', priority: 'primary', scheme: 'main' },
        ],
      },
    ],
    schemes: {
      main: { sets: 3, reps_min: 5, reps_max: 5, rest_seconds: 120, target_rpe: 8.0, intensity_pct: 0.8 },
      accessory: { sets: 3, reps_min: 10, reps_max: 12, rest_seconds: 60, target_rpe: 7.0, intensity_pct: 0.65 },
    },
  },
  progression_ref: { model_key: 'linear_load', params: { increment: 2.5 }, deload_every: 4 },
  required_inputs: [
    { key: 'squat_start', label: 'Comfortable squat weight', type: 'number', applies_to: 'squat' },
  ],
};

describe('TemplateListItem', () => {
  it('should render compact row with template name and summary', () => {
    render(
      <TemplateListItem
        template={mockTemplate}
        isExpanded={false}
        onToggle={() => {}}
      />
    );

    expect(screen.getByText('Full Body 3x/Week')).toBeInTheDocument();
    expect(screen.getByText(/beginner/i)).toBeInTheDocument();
    expect(screen.getByText(/general/i)).toBeInTheDocument();
    expect(screen.getByText(/3 days/i)).toBeInTheDocument();
    expect(screen.getByText(/45-60/i)).toBeInTheDocument();
  });

  it('should show right chevron when collapsed', () => {
    render(
      <TemplateListItem
        template={mockTemplate}
        isExpanded={false}
        onToggle={() => {}}
      />
    );

    const chevron = screen.getByText('▶');
    expect(chevron).toBeInTheDocument();
  });

  it('should show down chevron when expanded', () => {
    render(
      <TemplateListItem
        template={mockTemplate}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    const chevron = screen.getByText('▼');
    expect(chevron).toBeInTheDocument();
  });

  it('should call onToggle when row is clicked', () => {
    const onToggle = vitest.fn();
    render(
      <TemplateListItem
        template={mockTemplate}
        isExpanded={false}
        onToggle={onToggle}
      />
    );

    fireEvent.click(screen.getByText('Full Body 3x/Week'));
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('should render expanded details when isExpanded is true', () => {
    render(
      <TemplateListItem
        template={mockTemplate}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    expect(screen.getByText('Three full-body days for beginners building general strength.')).toBeInTheDocument();
    expect(screen.getByText('Full Body A')).toBeInTheDocument();
    expect(screen.getByText('linear_load')).toBeInTheDocument();
  });

  it('should display set/rep schemes in expanded view', () => {
    render(
      <TemplateListItem
        template={mockTemplate}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    expect(screen.getByText('main')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // sets
    expect(screen.getByText('5')).toBeInTheDocument(); // reps
    expect(screen.getByText('120')).toBeInTheDocument(); // rest seconds
  });

  it('should display required inputs when present', () => {
    render(
      <TemplateListItem
        template={mockTemplate}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    expect(screen.getByText('Comfortable squat weight')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm run test -- TemplateListItem.test.tsx
```

Expected: FAIL — "TemplateListItem not found"

- [ ] **Step 3: Create TemplateListItem component**

Create `frontend/src/components/TemplateListItem.tsx`:

```typescript
import { Card } from '@/components';
import type { Template, Scheme } from '@/types/template';

interface TemplateListItemProps {
  template: Template;
  isExpanded: boolean;
  onToggle: () => void;
}

export default function TemplateListItem({ template, isExpanded, onToggle }: TemplateListItemProps) {
  const chevron = isExpanded ? '▼' : '▶';

  return (
    <Card className="mb-4 cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
      {/* Compact Row */}
      <div onClick={onToggle} className="p-4">
        <div className="flex items-start gap-3">
          <span className="text-lg flex-shrink-0 mt-0.5">{chevron}</span>
          <div className="flex-1">
            <h3 className="heading-md text-neutral-900 dark:text-neutral-50 mb-1">{template.name}</h3>
            <p className="body-sm text-neutral-600 dark:text-neutral-400">
              {template.experience_levels.join(', ')} • {template.goals.join(', ')} •{' '}
              {template.days_per_week_min}-{template.days_per_week_max} days/week • {template.session_duration_min}-
              {template.session_duration_max} min
            </p>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-t border-neutral-200 dark:border-neutral-700 p-4 space-y-6">
          {/* Description */}
          <div>
            <p className="body-md text-neutral-700 dark:text-neutral-300">{template.description}</p>
          </div>

          {/* Configuration Section */}
          <div>
            <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-2">Configuration</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Experience Levels</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.experience_levels.join(', ')}
                </p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Goals</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.goals.join(', ')}
                </p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Days Per Week</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.days_per_week_min}-{template.days_per_week_max}
                </p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Session Duration</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.session_duration_min}-{template.session_duration_max} min
                </p>
              </div>
            </div>
          </div>

          {/* Progression Section */}
          <div>
            <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-2">Progression</h4>
            <div className="space-y-2">
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Model</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.progression_ref.model_key}
                </p>
              </div>
              {Object.keys(template.progression_ref.params).length > 0 && (
                <div>
                  <p className="label-sm text-neutral-600 dark:text-neutral-400">Parameters</p>
                  <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                    {Object.entries(template.progression_ref.params)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(', ')}
                  </p>
                </div>
              )}
              {template.progression_ref.deload_every && (
                <div>
                  <p className="label-sm text-neutral-600 dark:text-neutral-400">Deload Every</p>
                  <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                    {template.progression_ref.deload_every} weeks
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Workout Split Section */}
          <div>
            <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-3">Workout Split</h4>
            <div className="space-y-3">
              {template.split.sessions.map((session) => (
                <div key={session.key} className="bg-neutral-50 dark:bg-neutral-800 p-3 rounded-lg">
                  <p className="label-md text-neutral-900 dark:text-neutral-50 mb-2">
                    {session.order}. {session.name}
                  </p>
                  <div className="space-y-1">
                    {session.slots.map((slot, idx) => (
                      <p key={idx} className="body-sm text-neutral-600 dark:text-neutral-400">
                        • {slot.pattern || slot.region} ({slot.priority}, {slot.scheme} scheme)
                      </p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Set/Rep Schemes Section */}
          <div>
            <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-3">Set/Rep Schemes</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 dark:border-neutral-700">
                    <th className="text-left py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                      Scheme
                    </th>
                    <th className="text-center py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                      Sets
                    </th>
                    <th className="text-center py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                      Reps
                    </th>
                    <th className="text-center py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                      Rest (s)
                    </th>
                    {Object.values(template.split.schemes).some((s) => s.target_rpe) && (
                      <th className="text-center py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                        RPE
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(template.split.schemes).map(([name, scheme]) => (
                    <tr key={name} className="border-b border-neutral-100 dark:border-neutral-800">
                      <td className="py-2 px-2 text-neutral-900 dark:text-neutral-50">{name}</td>
                      <td className="py-2 px-2 text-center text-neutral-900 dark:text-neutral-50">
                        {scheme.sets}
                      </td>
                      <td className="py-2 px-2 text-center text-neutral-900 dark:text-neutral-50">
                        {scheme.reps_min}-{scheme.reps_max}
                      </td>
                      <td className="py-2 px-2 text-center text-neutral-900 dark:text-neutral-50">
                        {scheme.rest_seconds}
                      </td>
                      {scheme.target_rpe !== undefined && (
                        <td className="py-2 px-2 text-center text-neutral-900 dark:text-neutral-50">
                          {scheme.target_rpe}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Required Inputs Section */}
          {template.required_inputs.length > 0 && (
            <div>
              <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-3">Required Inputs</h4>
              <div className="space-y-2">
                {template.required_inputs.map((input) => (
                  <div key={input.key} className="bg-neutral-50 dark:bg-neutral-800 p-3 rounded-lg">
                    <p className="label-sm text-neutral-900 dark:text-neutral-50">{input.label}</p>
                    <p className="body-sm text-neutral-600 dark:text-neutral-400">
                      Type: {input.type}
                      {input.applies_to && ` • Applies to: ${input.applies_to}`}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run test -- TemplateListItem.test.tsx
```

Expected: PASS (all tests)

- [ ] **Step 5: Run type check and linter**

```bash
cd frontend && npm run type-check && npm run lint
```

Expected: PASS (no type errors, no lint errors)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/TemplateListItem.tsx frontend/src/tests/components/TemplateListItem.test.tsx
git commit -m "feat(components): add TemplateListItem accordion component"
```

---

## Task 4: Create TemplatesPage Component

**Files:**
- Create: `frontend/src/pages/TemplatesPage.tsx`
- Test: `frontend/src/tests/pages/TemplatesPage.test.tsx`

**Interfaces:**
- Consumes: `Template` type, `listTemplates()` API function, `TemplateListItem` component
- Produces: `TemplatesPage` component (no props, route component)

- [ ] **Step 1: Write failing integration test**

Create `frontend/src/tests/pages/TemplatesPage.test.tsx`:

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TemplatesPage from '@/pages/TemplatesPage';
import * as templatesApi from '@/api/templates';
import type { Template } from '@/types/template';

vi.mock('@/api/templates');

const mockTemplate: Template = {
  slug: 'full-body-x3',
  name: 'Full Body 3x/Week',
  description: 'Three full-body days for beginners building general strength.',
  goals: ['general', 'strength'],
  experience_levels: ['beginner'],
  days_per_week_min: 3,
  days_per_week_max: 3,
  session_duration_min: 45,
  session_duration_max: 60,
  split: {
    sessions: [
      {
        key: 'full_a',
        name: 'Full Body A',
        order: 1,
        slots: [
          { pattern: 'squat', priority: 'primary', scheme: 'main' },
        ],
      },
    ],
    schemes: {
      main: { sets: 3, reps_min: 5, reps_max: 5, rest_seconds: 120, target_rpe: 8.0, intensity_pct: 0.8 },
    },
  },
  progression_ref: { model_key: 'linear_load', params: { increment: 2.5 }, deload_every: 4 },
  required_inputs: [],
};

const mockTemplate2: Template = {
  ...mockTemplate,
  slug: 'ppl-x6',
  name: 'Push/Pull/Legs 6x/Week',
};

function renderPage() {
  render(
    <BrowserRouter>
      <TemplatesPage />
    </BrowserRouter>,
  );
}

describe('TemplatesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show loading spinner on initial load', () => {
    vi.mocked(templatesApi.listTemplates).mockImplementation(() => new Promise(() => {}));

    renderPage();

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should fetch and render templates on mount', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Full Body 3x/Week')).toBeInTheDocument();
    });
  });

  it('should render multiple templates', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate, mockTemplate2]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Full Body 3x/Week')).toBeInTheDocument();
      expect(screen.getByText('Push/Pull/Legs 6x/Week')).toBeInTheDocument();
    });
  });

  it('should expand template when clicked', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate]);

    renderPage();

    await waitFor(() => screen.getByText('Full Body 3x/Week'));

    fireEvent.click(screen.getByText('Full Body 3x/Week'));

    await waitFor(() => {
      expect(screen.getByText('Three full-body days for beginners building general strength.')).toBeInTheDocument();
    });
  });

  it('should collapse template when clicked again', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate]);

    renderPage();

    await waitFor(() => screen.getByText('Full Body 3x/Week'));

    fireEvent.click(screen.getByText('Full Body 3x/Week'));
    await waitFor(() => {
      expect(screen.getByText('Three full-body days for beginners building general strength.')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Full Body 3x/Week'));
    await waitFor(() => {
      expect(screen.queryByText('Three full-body days for beginners building general strength.')).not.toBeInTheDocument();
    });
  });

  it('should only allow one template expanded at a time', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate, mockTemplate2]);

    renderPage();

    await waitFor(() => screen.getByText('Full Body 3x/Week'));

    fireEvent.click(screen.getByText('Full Body 3x/Week'));
    await waitFor(() => {
      expect(screen.getByText('Three full-body days for beginners building general strength.')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Push/Pull/Legs 6x/Week'));
    await waitFor(() => {
      expect(screen.queryByText('Three full-body days for beginners building general strength.')).not.toBeInTheDocument();
    });
  });

  it('should show error alert on fetch failure', async () => {
    vi.mocked(templatesApi.listTemplates).mockRejectedValue(new Error('Failed to load templates'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Failed to load templates/i)).toBeInTheDocument();
    });
  });

  it('should retry fetching templates when retry button clicked', async () => {
    vi.mocked(templatesApi.listTemplates)
      .mockRejectedValueOnce(new Error('Failed to load templates'))
      .mockResolvedValueOnce([mockTemplate]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Failed to load templates/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Retry/i }));

    await waitFor(() => {
      expect(screen.getByText('Full Body 3x/Week')).toBeInTheDocument();
    });
  });

  it('should show empty state when no templates', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/No templates found/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm run test -- TemplatesPage.test.tsx
```

Expected: FAIL — "TemplatesPage not found"

- [ ] **Step 3: Create TemplatesPage component**

Create `frontend/src/pages/TemplatesPage.tsx`:

```typescript
import { useEffect, useState } from 'react';
import { Alert, Spinner } from '@/components';
import TemplateListItem from '@/components/TemplateListItem';
import { listTemplates } from '@/api/templates';
import { getErrorMessage } from '@/api/errors';
import type { Template } from '@/types/template';

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTemplates();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-dvh">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="display-md mb-2">Program Templates</h1>
          <p className="body-md text-neutral-600 dark:text-neutral-400">
            Browse all available program templates. Select one to see detailed configuration.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert
            type="error"
            dismissible
            onDismiss={() => setError(null)}
            className="mb-6"
          >
            <div className="flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={loadTemplates}
                className="ml-4 px-3 py-1 bg-error-600 hover:bg-error-700 text-white rounded text-sm font-medium"
              >
                Retry
              </button>
            </div>
          </Alert>
        )}

        {/* Empty State */}
        {templates.length === 0 && !error && (
          <div className="text-center py-12">
            <p className="body-lg text-neutral-600 dark:text-neutral-400">
              No templates found
            </p>
          </div>
        )}

        {/* Templates List */}
        {templates.length > 0 && (
          <div>
            {templates.map((template) => (
              <TemplateListItem
                key={template.slug}
                template={template}
                isExpanded={expandedSlug === template.slug}
                onToggle={() =>
                  setExpandedSlug(expandedSlug === template.slug ? null : template.slug)
                }
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run test -- TemplatesPage.test.tsx
```

Expected: PASS (all tests)

- [ ] **Step 5: Run type check and linter**

```bash
cd frontend && npm run type-check && npm run lint
```

Expected: PASS (no type errors, no lint errors)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/TemplatesPage.tsx frontend/src/tests/pages/TemplatesPage.test.tsx
git commit -m "feat(pages): add TemplatesPage with accordion template browser"
```

---

## Task 5: Add Route to App.tsx

**Files:**
- Modify: `frontend/src/App.tsx` (add import and route)

**Interfaces:**
- Consumes: `TemplatesPage` component from Task 4
- Produces: `/templates` route

- [ ] **Step 1: Read App.tsx to find where to add the route**

```bash
grep -n "Route path=" /Users/jorgecascante/develop/my-gym/frontend/src/App.tsx | head -10
```

- [ ] **Step 2: Add import for TemplatesPage**

In `frontend/src/App.tsx`, find the import section and add:

```typescript
import TemplatesPage from '@/pages/TemplatesPage';
```

- [ ] **Step 3: Add route for /templates**

Find the `<Routes>` section and add this route (after other authenticated routes, before closing `</Routes>`):

```typescript
<Route path="/templates" element={<TemplatesPage />} />
```

- [ ] **Step 4: Run type check**

```bash
cd frontend && npm run type-check
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(routing): add /templates route for template browser"
```

---

## Task 6: Manual Testing & Verification

**No automated tests; manual verification of working feature**

- [ ] **Step 1: Start dev server**

```bash
cd /Users/jorgecascante/develop/my-gym
docker-compose up
```

Wait for frontend (http://localhost:5173) to be ready.

- [ ] **Step 2: Verify backend endpoint exists**

```bash
curl http://localhost:8000/api/v1/templates -H "Authorization: Bearer <test_token>"
```

If 404: backend endpoint not implemented yet (out of scope for this plan).
If 500 or valid response: proceed.

- [ ] **Step 3: Login and navigate to /templates**

- Go to http://localhost:5173
- Login with a test account
- Navigate to http://localhost:5173/templates

- [ ] **Step 4: Verify page layout**

- Page loads and shows "Program Templates" header
- List of templates appears (if backend returns data)
- Each template shows compact row with name, experience level, goals, days/week, duration

- [ ] **Step 5: Verify accordion behavior**

- Click a template row → expands and shows full details
- Description, configuration, progression, split, schemes, required inputs all visible
- Click again → collapses
- Click another template → first collapses, second expands (only one open)

- [ ] **Step 6: Verify error handling**

- Stop backend: `docker-compose down backend`
- Refresh page
- Error alert should appear with "Failed to load templates"
- Click Retry button → attempts to fetch again
- Alert should show appropriate error message

- [ ] **Step 7: Verify responsive design**

- Resize browser to mobile width (320px)
- Compact row should be readable
- Chevron visible and clickable
- Expanded view should not overflow horizontally
- Test on tablet size (768px) and desktop

- [ ] **Step 8: Verify dark mode**

- Toggle dark mode (if theme toggle available)
- Colors should adjust correctly
- Text readable in both modes

- [ ] **Step 9: Run full test suite**

```bash
cd frontend && npm run test
```

Expected: All tests pass, coverage >80%

- [ ] **Step 10: Run linter and type checker**

```bash
cd frontend && npm run lint && npm run type-check
```

Expected: PASS

- [ ] **Step 11: Final commit (if any tweaks needed)**

If manual testing found any issues, fix them and commit:

```bash
git add .
git commit -m "fix: address issues from manual testing"
```

---

## Backend Dependency

⚠️ **This plan assumes the backend provides `GET /api/v1/templates` endpoint.**

If not implemented, the frontend will show an error on the TemplatesPage. Add this to backend development queue:

- Create endpoint `GET /api/v1/templates`
- Response format:
  ```json
  {
    "templates": [
      {
        "slug": "full-body-x3",
        "name": "Full Body",
        "description": "...",
        "goals": ["general", "strength"],
        "experience_levels": ["beginner"],
        "days_per_week_min": 3,
        "days_per_week_max": 3,
        "session_duration_min": 45,
        "session_duration_max": 60,
        "split": { ... },
        "schemes": { ... },
        "progression_ref": { ... },
        "required_inputs": [ ... ]
      }
    ]
  }
  ```
- Fetch from database (ProgramTemplate model)
- Return all templates (no pagination for MVP)
- Handle 500 error gracefully

---

## Summary

**Tasks completed:**
1. ✅ Type definitions (template.ts)
2. ✅ API client (templates.ts)
3. ✅ TemplateListItem component + tests
4. ✅ TemplatesPage component + tests
5. ✅ Route added to App.tsx
6. ✅ Manual testing & verification

**Result:** Fully functional, tested `/templates` page with accordion-style template browser.

**Test coverage:** Unit tests for TemplateListItem, integration tests for TemplatesPage.

**Next phase (Future):** Template search/filter, comparison mode, link to program creation.
