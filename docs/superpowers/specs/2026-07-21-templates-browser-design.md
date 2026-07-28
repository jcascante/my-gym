# Templates Browser Design

**Date:** 2026-07-21
**Status:** Design approved
**Scope:** Read-only UI module to browse and view all available program templates with their configurations

## Overview

A dedicated `/templates` page that displays all available program templates in a read-only accordion-style list. Users see a compact summary of each template and can expand to view full configuration details (split structure, exercise schemes, progression model, required inputs).

## User Story

As a user, I want to browse all available program templates and understand their structure and requirements, so I can make informed decisions when selecting a template for program generation.

## Page Architecture

### URL & Route
- **Route:** `/templates`
- **Authentication:** Required (authenticated users only)
- **Layout:** Follows EnvironmentsPage pattern with vertical card stack

### Component Structure

```
TemplatesPage
├── Page header (title, subtitle)
├── Error alert (if fetch fails)
├── Loading spinner (while fetching)
├── TemplateList
│   └── TemplateListItem (one per template)
│       ├── Compact row (always visible)
│       └── Expanded details (conditional)
└── Empty state (if no templates)
```

### Files to Create

1. **`src/pages/TemplatesPage.tsx`** - Main page component
2. **`src/components/TemplateListItem.tsx`** - Individual template list item with expand/collapse
3. **`src/api/templates.ts`** - API client for fetching templates
4. **`src/types/template.ts`** - TypeScript types for template data (if not already present)

## Data Model

### Template Data Structure

Fetched from `GET /api/v1/templates`:

```typescript
interface Template {
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
  progression_ref: {
    model_key: string;
    params: Record<string, unknown>;
    deload_every?: number;
  };
  required_inputs: RequiredInput[];
}

interface Session {
  key: string;
  name: string;
  order: number;
  slots: Slot[];
}

interface Slot {
  pattern?: string;
  region?: string;
  priority: string;
  scheme: string;
  muscles?: string[];
}

interface Scheme {
  sets: number;
  reps_min: number;
  reps_max: number;
  rest_seconds: number;
  target_rpe?: number;
  intensity_pct?: number;
}

interface RequiredInput {
  key: string;
  label: string;
  type: "number" | "text";
  applies_to?: string;
}
```

## UI Layout

### Compact Row (Collapsed)

**Visual:**
```
▶ Full Body 3x/Week
  Beginner • Strength, General • 3 days/week • 45-60 min
```

**Display Logic:**
- Chevron icon (pointing right when collapsed)
- Template name (prominent)
- Experience levels (comma-separated)
- Goals (comma-separated)
- Days per week range
- Session duration range

**Interactions:**
- Click anywhere on row → toggle expand
- Chevron rotates to point down when expanded

### Expanded Details (Inline)

Shows all template configuration:

1. **Header** - Same as compact row with chevron pointing down
2. **Description** - Full template description
3. **Configuration Section**
   - Experience levels (array)
   - Goals (array)
   - Days per week (min-max)
   - Session duration (min-max)
4. **Progression Section**
   - Model name (e.g., "linear_load", "double_progression")
   - Parameters (e.g., increment: 2.5)
   - Deload frequency (if applicable)
5. **Workout Split Section**
   - Each session/day listed with:
     - Session name and order
     - Slots (exercise patterns/regions with priority and scheme)
6. **Set/Rep Schemes Section**
   - Table or grid showing:
     - Scheme name (main, accessory, etc.)
     - Sets, reps range, rest, target RPE, intensity %
7. **Required Inputs Section** (if any)
   - Label, type, applies to (which movement or slot)

### Page States

**Loading:**
- Full-page spinner centered
- "Loading templates..."

**Empty:**
- Message: "No templates found"
- Probably won't happen in normal operation

**Error:**
- Alert banner with error message
- Retry button to refetch

**Loaded:**
- List of all templates, collapsed by default
- First template optionally expanded for discoverability

## State Management

**TemplatesPage state:**
```typescript
const [templates, setTemplates] = useState<Template[]>([]);
const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
```

**Accordion behavior:**
- `expandedSlug` tracks which template is currently expanded
- Clicking a row calls `setExpandedSlug(slug === expandedSlug ? null : slug)`
- Only one template can be expanded at a time

## API Integration

### Endpoint

**Backend must provide:**
```
GET /api/v1/templates
```

**Response:**
```json
{
  "templates": [
    {
      "slug": "full-body-x3",
      "name": "Full Body",
      ...all template fields...
    }
  ]
}
```

**Error handling:**
- Network error → show "Failed to load templates. Please try again."
- 401/403 → redirect to login (handled by parent router)
- 500 → show "Server error loading templates"

### Implementation (Frontend)

Create `src/api/templates.ts`:
```typescript
export async function listTemplates(): Promise<Template[]> {
  const response = await fetch('/api/v1/templates');
  if (!response.ok) throw new Error('Failed to fetch templates');
  const data = await response.json();
  return data.templates;
}
```

## Styling & Theming

**Uses existing design system:**
- Tailwind CSS utilities
- `src/styles/theme.ts` design tokens
- Dark mode support via CSS classes
- Responsive breakpoints (mobile-first)

**Component styling:**
- Reuse `Card` component for list items
- Chevron icon (can use SVG or Unicode ▶/▼)
- Spacing: consistent with EnvironmentsPage
- Typography: heading/label/body classes from design tokens

## Testing Strategy

**Unit tests (TemplateListItem):**
- Renders compact row correctly
- Click expands/collapses
- Only one item expanded at a time
- Displays all expanded fields correctly

**Integration tests (TemplatesPage):**
- Fetches templates on mount
- Shows loading spinner
- Renders list of templates
- Handles API errors gracefully
- Shows empty state if no templates

**Manual testing:**
- Expand multiple templates, verify accordion behavior
- Mobile responsive (touch-friendly expand)
- Dark mode appearance
- Authenticated route access

## Non-Requirements (Out of Scope)

- Template filtering or search
- Sorting templates
- Creating/editing templates from UI
- Template comparison side-by-side
- Export template configuration
- Pagination (load all templates at once)

## Future Enhancements

- Search/filter by goals, experience level, days per week
- Template comparison (expand two side-by-side)
- Copy template JSON for documentation
- Template ratings or usage stats
- Link from templates to "Create Program" with template pre-selected
