# Program Builder — Frontend Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React program-builder wizard (`match → select → required inputs → review/adapt → accept`) plus a read-only preview, against the Plan 1 backend endpoints.

**Architecture:** A single `ProgramBuilderPage` drives four stages via step state; TanStack Query owns server state and each feedback action refetches the draft. Reuses the existing component library and `ProgramCreationForm`.

**Tech Stack:** React 19 + TypeScript, Vite, React Router, Zustand, TanStack Query, Vitest + React Testing Library, Tailwind.

## Global Constraints

- **Prerequisite:** Plan 1 backend endpoints are live (`/programs/match`, `/draft`, `/{id}/preview`, `/{id}/feedback`, `/{id}/slots/{we_id}/alternatives`, `/{id}/accept`, `/{id}`).
- **Scope addition (decided before Task 1, 2026-07-16):** Plan 1 deleted the old bare `POST /programs` 501-stub endpoint when it replaced `app/api/v1/endpoints/programs.py` with the real engine router — so today's `ProgramCreationForm` (embedded in `EnvironmentsPage`, calling `createProgram()`) is already broken on this branch, not just superseded. This plan now also retires that legacy flow: `ProgramCreationForm` becomes the wizard's "Preferences" step (presentational, `onSubmit`-driven, no internal API call), and `EnvironmentsPage`'s "Generate Program" action navigates to the wizard instead of embedding the form. See the added steps in Task 2 and Task 7, and the amended CTA in Task 8.
- **`fitness_focus` is a goal tag, not a body part:** the backend matches `inp.fitness_focus in template.goals` against seeded values `"general" | "strength" | "muscle_gain"` (`backend/app/db/seed/program_templates.py`). This is unrelated to the old `FocusArea` enum (push/pull/legs/...) that `ProgramCreationForm` used for its `focus_areas` multi-select — that field is being dropped, not converted. `preferred_days`, `start_date`, `available_weight_increments`, and `progression_style` are also dropped from the form: nothing in the new engine consumes them (confirmed via grep — only the now-orphaned `backend/app/schemas/program.py` still defines them).
- All API calls go through `apiClient` (`src/api/client.ts`, `withCredentials`).
- TDD: Vitest + RTL, user-centric queries (`getByRole`/`getByText`), per `react-component-testing`.
- Follow the existing Tailwind design system (responsive, accessible, keyboard-navigable).
- Components exported from `src/components/index.ts`; strict TypeScript.
- Commit after every green test.

---

### Task 0: Retire legacy form stub (refactor ProgramCreationForm)

**Files:**
- Modify: `frontend/src/components/ProgramCreationForm.tsx`, `frontend/src/tests/components/ProgramCreationForm.test.tsx`
- Modify: `frontend/src/pages/EnvironmentsPage.tsx`, `frontend/src/tests/pages/EnvironmentsPage.test.tsx`
- Delete: `frontend/src/api/programs.ts` `createProgram()` export + its tests (`frontend/src/tests/api/programs.test.ts` covering it)

**Why:** Plan 1 deleted the backend's `POST /programs` 501-stub endpoint when it replaced `app/api/v1/endpoints/programs.py` with the real engine. The old form (in `EnvironmentsPage`) called `createProgram()` which POSTed to that stub—it's now broken on this branch. Option 3: retire it cleanly: strip `createProgram()` from the API module (test removes its stub import), make `ProgramCreationForm` presentational-only (`onSubmit` callback required, no internal API call), and have `EnvironmentsPage`'s "Generate Program" button navigate to `/programs/new` (the wizard) instead of embedding the form.

- [ ] **Step 1: Refactor `ProgramCreationForm.tsx`** — remove internal `createProgram()` call, drop unused fields (`preferred_days`, `start_date`, `focus_areas`, `available_weight_increments`, `progression_style`), keep only what the wizard needs (environment_id, days_per_week, session_duration_min, weight_unit). Add required `onSubmit: (values: MatchRequest) => void` prop. Remove result/error UI (let caller handle feedback).

- [ ] **Step 2: Update `ProgramCreationForm.test.tsx`** — remove tests asserting the old 501-stub behavior and internal POST; test that `onSubmit` callback is invoked with collected values. Verify the form is now a pure controlled component.

- [ ] **Step 3: Update `EnvironmentsPage.tsx`** — replace the `{ mode: 'generate' }` panel rendering a `<ProgramCreationForm />` with a `<Link to="/programs/new"><Button>Generate Program</Button></Link>` (or a direct button that navigates). Simplify `PanelState` to remove the `'generate'` mode.

- [ ] **Step 4: Update `EnvironmentsPage.test.tsx`** — remove tests for the old embedded-form flow; add a test that clicking the button navigates to `/programs/new` (or asserts the link's href).

- [ ] **Step 5: Remove `createProgram()` from `frontend/src/api/programs.ts`** — keep all other exports (`matchTemplates`, `createDraft`, etc., added in Task 2); delete the old stub POST.

- [ ] **Step 6: Clean up test coverage** — if `frontend/src/tests/api/programs.test.ts` has tests for `createProgram()`, remove them. Task 2 will add tests for the real program API functions.

- [ ] **Step 7: Run tests** — `docker-compose exec frontend npm run test` should pass with old stub coverage gone and refactored form tests in place.

- [ ] **Step 8: Commit** — `git commit -m "feat(program-ui): retire legacy form stub, make ProgramCreationForm presentational"`

---

### Task 1: Program API types

**Files:**
- Create: `frontend/src/types/program.ts`
- Test: none (types only; validated by consumers).

**Interfaces:**
- Produces: `TemplateMatch`, `RequiredInput`, `SlotPreview`, `WorkoutPreview`, `ProgramPreview`, `MatchRequest`, `DraftRequest`, `FeedbackAction`, `Alternative`.

- [ ] **Step 1: Create the types (mirror Plan 1 `program_api.py`)**

```typescript
// frontend/src/types/program.ts
export interface RequiredInput { key: string; label: string; type: 'number' | 'text'; applies_to: string | null }

export interface TemplateMatch {
  template_id: number; slug: string; name: string; fit_pct: number;
  factors: Record<string, number>; required_inputs: RequiredInput[];
}

export interface SlotPreview {
  workout_exercise_id: number; exercise_id: number; sets: number; reps: number;
  load: number | null; rest_seconds: number; note: string | null;
  is_locked: boolean; is_user_swapped: boolean;
}

export interface WorkoutPreview { workout_id: number; key: string; name: string; slots: SlotPreview[] }

export interface ProgramPreview {
  program_id: number; name: string; status: 'draft' | 'active' | 'archived';
  duration_weeks: number; weeks: Record<string, WorkoutPreview[]>;
}

export interface MatchRequest {
  environment_id: number; days_per_week: number; session_duration_min: number;
  fitness_focus: string; weight_unit: string; duration_weeks: number;
}

export interface DraftRequest extends MatchRequest { template_id: number; required_inputs: Record<string, number | string> }

export type FeedbackAction =
  | { type: 'lock' | 'exclude' | 'regenerate'; workout_exercise_id: number }
  | { type: 'swap'; workout_exercise_id: number; exercise_id: number }
  | { type: 'adjust_volume'; workout_key: string; delta: number };

export interface Alternative { id: number; name: string; slug: string }
```

- [ ] **Step 2: Commit** — `git commit -m "feat(program-ui): program api types"`

---

### Task 2: API client functions

**Files:**
- Rewrite: `frontend/src/api/programs.ts`
- Test: `frontend/src/tests/api/programs.test.ts`

**Interfaces:**
- Produces: `matchTemplates`, `createDraft`, `getProgramPreview`, `submitFeedback`, `getSlotAlternatives`, `acceptProgram`.

- [ ] **Step 1: Write the failing test (mock `apiClient`)**

```typescript
// frontend/src/tests/api/programs.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '@/api/client';
import { matchTemplates, submitFeedback } from '@/api/programs';

vi.mock('@/api/client', () => ({ apiClient: { post: vi.fn(), get: vi.fn() } }));

describe('programs api', () => {
  beforeEach(() => vi.clearAllMocks());

  it('posts match request', async () => {
    (apiClient.post as any).mockResolvedValue({ data: [{ template_id: 1 }] });
    const res = await matchTemplates({ environment_id: 1, days_per_week: 3, session_duration_min: 60, fitness_focus: 'strength', weight_unit: 'kg', duration_weeks: 8 });
    expect(apiClient.post).toHaveBeenCalledWith('/programs/match', expect.any(Object));
    expect(res[0].template_id).toBe(1);
  });

  it('posts feedback to program id', async () => {
    (apiClient.post as any).mockResolvedValue({ data: { program_id: 5 } });
    await submitFeedback(5, { type: 'lock', workout_exercise_id: 9 });
    expect(apiClient.post).toHaveBeenCalledWith('/programs/5/feedback', { type: 'lock', workout_exercise_id: 9 });
  });
});
```

- [ ] **Step 2: Run and confirm failure** — `docker-compose exec frontend npm run test -- programs.test.ts`

- [ ] **Step 3: Implement**

```typescript
// frontend/src/api/programs.ts
import { apiClient } from '@/api/client';
import type {
  Alternative, DraftRequest, FeedbackAction, MatchRequest, ProgramPreview, TemplateMatch,
} from '@/types/program';

export async function matchTemplates(req: MatchRequest): Promise<TemplateMatch[]> {
  const { data } = await apiClient.post<TemplateMatch[]>('/programs/match', req);
  return data;
}

export async function createDraft(req: DraftRequest): Promise<ProgramPreview> {
  const { data } = await apiClient.post<ProgramPreview>('/programs/draft', req);
  return data;
}

export async function getProgramPreview(id: number): Promise<ProgramPreview> {
  const { data } = await apiClient.get<ProgramPreview>(`/programs/${id}/preview`);
  return data;
}

export async function submitFeedback(id: number, action: FeedbackAction): Promise<ProgramPreview> {
  const { data } = await apiClient.post<ProgramPreview>(`/programs/${id}/feedback`, action);
  return data;
}

export async function getSlotAlternatives(id: number, weId: number): Promise<Alternative[]> {
  const { data } = await apiClient.get<Alternative[]>(`/programs/${id}/slots/${weId}/alternatives`);
  return data;
}

export async function acceptProgram(id: number): Promise<ProgramPreview> {
  const { data } = await apiClient.post<ProgramPreview>(`/programs/${id}/accept`);
  return data;
}
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(program-ui): program api client functions"`

---

### Task 3: Ensure TanStack Query provider + builder hooks

**Files:**
- Modify (if missing): `frontend/src/main.tsx` (wrap app in `QueryClientProvider`)
- Create: `frontend/src/hooks/usePrograms.ts`
- Test: `frontend/src/tests/hooks/usePrograms.test.tsx`

**Interfaces:**
- Produces: `useMatchTemplates()`, `useCreateDraft()`, `useProgramPreview(id)`, `useSubmitFeedback(id)`, `useSlotAlternatives(id, weId, enabled)`, `useAcceptProgram(id)`.

- [ ] **Step 1: Verify the provider exists**

Run: `grep -rn "QueryClientProvider" frontend/src`
If absent, wrap the root in `frontend/src/main.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
const queryClient = new QueryClient();
// <QueryClientProvider client={queryClient}> <App /> </QueryClientProvider>
```

- [ ] **Step 2: Write the failing test**

```tsx
// frontend/src/tests/hooks/usePrograms.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMatchTemplates } from '@/hooks/usePrograms';
import * as api from '@/api/programs';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useMatchTemplates', () => {
  it('returns matches on mutate', async () => {
    vi.spyOn(api, 'matchTemplates').mockResolvedValue([{ template_id: 1, slug: 's', name: 'n', fit_pct: 90, factors: {}, required_inputs: [] }]);
    const { result } = renderHook(() => useMatchTemplates(), { wrapper });
    result.current.mutate({ environment_id: 1, days_per_week: 3, session_duration_min: 60, fitness_focus: 'strength', weight_unit: 'kg', duration_weeks: 8 });
    await waitFor(() => expect(result.current.data?.[0].template_id).toBe(1));
  });
});
```

- [ ] **Step 3: Run and confirm failure.**

- [ ] **Step 4: Implement the hooks**

```tsx
// frontend/src/hooks/usePrograms.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  acceptProgram, createDraft, getProgramPreview, getSlotAlternatives, matchTemplates, submitFeedback,
} from '@/api/programs';
import type { DraftRequest, FeedbackAction, MatchRequest } from '@/types/program';

export const programKeys = { preview: (id: number) => ['program', id] as const };

export function useMatchTemplates() {
  return useMutation({ mutationFn: (req: MatchRequest) => matchTemplates(req) });
}

export function useCreateDraft() {
  return useMutation({ mutationFn: (req: DraftRequest) => createDraft(req) });
}

export function useProgramPreview(id: number | null) {
  return useQuery({
    queryKey: id ? programKeys.preview(id) : ['program', 'none'],
    queryFn: () => getProgramPreview(id as number),
    enabled: id != null,
  });
}

export function useSubmitFeedback(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (action: FeedbackAction) => submitFeedback(id, action),
    onSuccess: (data) => qc.setQueryData(programKeys.preview(id), data),
  });
}

export function useSlotAlternatives(id: number, weId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ['program', id, 'alternatives', weId],
    queryFn: () => getSlotAlternatives(id, weId as number),
    enabled: enabled && weId != null,
  });
}

export function useAcceptProgram(id: number) {
  return useMutation({ mutationFn: () => acceptProgram(id) });
}
```

- [ ] **Step 5: Run tests → PASS.**

- [ ] **Step 6: Commit** — `git commit -m "feat(program-ui): builder query hooks"`

---

### Task 4: Template match list + card

**Files:**
- Create: `frontend/src/components/TemplateMatchCard.tsx`, `frontend/src/components/TemplateMatchList.tsx`
- Modify: `frontend/src/components/index.ts`
- Test: `frontend/src/tests/components/TemplateMatchList.test.tsx`

**Interfaces:**
- Consumes: `TemplateMatch[]`.
- Produces: `<TemplateMatchList matches onSelect />`, `<TemplateMatchCard match selected onSelect />`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/tests/components/TemplateMatchList.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TemplateMatchList } from '@/components/TemplateMatchList';

const matches = [
  { template_id: 1, slug: 'ul', name: 'Upper/Lower x4', fit_pct: 92, factors: { goal: 1 }, required_inputs: [] },
  { template_id: 2, slug: 'fb', name: 'Full Body x3', fit_pct: 85, factors: { goal: 1 }, required_inputs: [] },
];

it('renders fit % and selects on click', async () => {
  const onSelect = vi.fn();
  render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
  expect(screen.getByText('92%')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /Upper\/Lower x4/ }));
  expect(onSelect).toHaveBeenCalledWith(matches[0]);
});
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/TemplateMatchCard.tsx
import { Card } from './Card';
import type { TemplateMatch } from '@/types/program';

export function TemplateMatchCard({ match, selected, onSelect }: {
  match: TemplateMatch; selected: boolean; onSelect: (m: TemplateMatch) => void;
}) {
  return (
    <button type="button" aria-pressed={selected} onClick={() => onSelect(match)}
      className={`w-full text-left focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg ${selected ? 'ring-2 ring-blue-600' : ''}`}>
      <Card>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{match.name}</h3>
          <span className="text-blue-600 font-bold">{match.fit_pct}%</span>
        </div>
        <ul className="mt-2 text-sm text-gray-600">
          {Object.entries(match.factors).map(([k, v]) => (
            <li key={k}>{k}: {Math.round(v * 100)}%</li>
          ))}
        </ul>
      </Card>
    </button>
  );
}
```

```tsx
// frontend/src/components/TemplateMatchList.tsx
import { TemplateMatchCard } from './TemplateMatchCard';
import type { TemplateMatch } from '@/types/program';

export function TemplateMatchList({ matches, selectedId, onSelect }: {
  matches: TemplateMatch[]; selectedId: number | null; onSelect: (m: TemplateMatch) => void;
}) {
  if (matches.length === 0) return <p className="text-gray-500">No matching templates for your setup.</p>;
  return (
    <div className="space-y-3">
      {matches.map((m) => (
        <TemplateMatchCard key={m.template_id} match={m} selected={m.template_id === selectedId} onSelect={onSelect} />
      ))}
    </div>
  );
}
```
Export both from `src/components/index.ts`.

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(program-ui): template match list"`

---

### Task 5: Required inputs form

**Files:**
- Create: `frontend/src/components/RequiredInputsForm.tsx`
- Modify: `frontend/src/components/index.ts`
- Test: `frontend/src/tests/components/RequiredInputsForm.test.tsx`

**Interfaces:**
- Consumes: `RequiredInput[]`.
- Produces: `<RequiredInputsForm inputs onSubmit />` calling `onSubmit(values: Record<string, number|string>)`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/tests/components/RequiredInputsForm.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RequiredInputsForm } from '@/components/RequiredInputsForm';

it('collects values and submits', async () => {
  const onSubmit = vi.fn();
  render(<RequiredInputsForm inputs={[{ key: 'squat_start', label: 'Squat weight', type: 'number', applies_to: 'squat' }]} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText('Squat weight'), '80');
  await userEvent.click(screen.getByRole('button', { name: /continue/i }));
  expect(onSubmit).toHaveBeenCalledWith({ squat_start: 80 });
});
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/RequiredInputsForm.tsx
import { useState } from 'react';
import { Button } from './Button';
import { FormField } from './FormField';
import type { RequiredInput } from '@/types/program';

export function RequiredInputsForm({ inputs, onSubmit }: {
  inputs: RequiredInput[]; onSubmit: (values: Record<string, number | string>) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const coerced: Record<string, number | string> = {};
    for (const inp of inputs) {
      const raw = values[inp.key] ?? '';
      coerced[inp.key] = inp.type === 'number' ? Number(raw) : raw;
    }
    onSubmit(coerced);
  };
  return (
    <form onSubmit={submit} className="space-y-4">
      {inputs.map((inp) => (
        <FormField key={inp.key} id={inp.key} label={inp.label} type={inp.type}
          value={values[inp.key] ?? ''}
          onChange={(e) => setValues((v) => ({ ...v, [inp.key]: e.target.value }))} />
      ))}
      <Button type="submit">Continue</Button>
    </form>
  );
}
```
> Match `FormField`'s actual prop names by reading `src/components/FormField.tsx`; adjust `id`/`label`/`value`/`onChange` if they differ.

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(program-ui): required inputs form"`

---

### Task 6: Draft view (week tabs, session card, slot row, feedback menu)

**Files:**
- Create: `frontend/src/components/WeekTabs.tsx`, `SessionCard.tsx`, `SlotRow.tsx`, `SlotFeedbackMenu.tsx`, `ExerciseAlternativesModal.tsx`, `DraftProgramView.tsx`
- Modify: `frontend/src/components/index.ts`
- Test: `frontend/src/tests/components/DraftProgramView.test.tsx`, `frontend/src/tests/components/SlotFeedbackMenu.test.tsx`

**Interfaces:**
- Consumes: `ProgramPreview`, `useSubmitFeedback`, `useSlotAlternatives`.
- Produces: `<DraftProgramView program programId />` (self-contained: renders week tabs + sessions + slots, wires feedback). `<SlotFeedbackMenu slot onAction />`. `<ExerciseAlternativesModal programId weId onPick onClose />`.

- [ ] **Step 1: Write the failing test (feedback menu emits actions)**

```tsx
// frontend/src/tests/components/SlotFeedbackMenu.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SlotFeedbackMenu } from '@/components/SlotFeedbackMenu';

const slot = { workout_exercise_id: 9, exercise_id: 3, sets: 3, reps: 5, load: 60, rest_seconds: 120, note: null, is_locked: false, is_user_swapped: false };

it('emits lock action', async () => {
  const onAction = vi.fn();
  render(<SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={() => {}} />);
  await userEvent.click(screen.getByRole('button', { name: /options/i }));
  await userEvent.click(screen.getByRole('menuitem', { name: /lock/i }));
  expect(onAction).toHaveBeenCalledWith({ type: 'lock', workout_exercise_id: 9 });
});
```

- [ ] **Step 2: Write the failing test (draft view renders weeks + slots)**

```tsx
// frontend/src/tests/components/DraftProgramView.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DraftProgramView } from '@/components/DraftProgramView';

vi.mock('@/hooks/usePrograms', () => ({
  useSubmitFeedback: () => ({ mutate: vi.fn(), isPending: false }),
  useSlotAlternatives: () => ({ data: [], isLoading: false }),
  programKeys: { preview: (id: number) => ['program', id] },
}));

const program = {
  program_id: 1, name: 'P', status: 'draft' as const, duration_weeks: 2,
  weeks: { '1': [{ workout_id: 1, key: 'a', name: 'Day A', slots: [
    { workout_exercise_id: 9, exercise_id: 3, sets: 3, reps: 5, load: 60, rest_seconds: 120, note: null, is_locked: true, is_user_swapped: false },
  ] }], '2': [] },
};

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

it('shows session, slot, and locked badge', () => {
  render(wrap(<DraftProgramView program={program} programId={1} />));
  expect(screen.getByText('Day A')).toBeInTheDocument();
  expect(screen.getByText(/3 × 5/)).toBeInTheDocument();
  expect(screen.getByLabelText(/locked/i)).toBeInTheDocument();
});
```

- [ ] **Step 3: Run and confirm both fail.**

- [ ] **Step 4: Implement the components**

```tsx
// frontend/src/components/SlotFeedbackMenu.tsx
import { useState } from 'react';
import type { FeedbackAction, SlotPreview } from '@/types/program';

export function SlotFeedbackMenu({ slot, onAction, onSwap }: {
  slot: SlotPreview; onAction: (a: FeedbackAction) => void; onSwap: () => void;
}) {
  const [open, setOpen] = useState(false);
  const id = slot.workout_exercise_id;
  return (
    <div className="relative">
      <button type="button" aria-label="options" onClick={() => setOpen((o) => !o)} className="px-2">⋯</button>
      {open && (
        <div role="menu" className="absolute right-0 z-10 bg-white shadow rounded border text-sm">
          <button role="menuitem" className="block w-full px-3 py-2 text-left" onClick={() => { onSwap(); setOpen(false); }}>Swap</button>
          <button role="menuitem" className="block w-full px-3 py-2 text-left" onClick={() => { onAction({ type: 'exclude', workout_exercise_id: id }); setOpen(false); }}>Exclude</button>
          <button role="menuitem" className="block w-full px-3 py-2 text-left" onClick={() => { onAction({ type: 'regenerate', workout_exercise_id: id }); setOpen(false); }}>Give me another</button>
          <button role="menuitem" className="block w-full px-3 py-2 text-left" onClick={() => { onAction({ type: 'lock', workout_exercise_id: id }); setOpen(false); }}>{slot.is_locked ? 'Locked' : 'Lock'}</button>
        </div>
      )}
    </div>
  );
}
```

```tsx
// frontend/src/components/SlotRow.tsx
import type { FeedbackAction, SlotPreview } from '@/types/program';
import { SlotFeedbackMenu } from './SlotFeedbackMenu';

export function SlotRow({ slot, onAction, onSwap }: {
  slot: SlotPreview; onAction: (a: FeedbackAction) => void; onSwap: () => void;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b">
      <div className="flex items-center gap-2">
        {slot.is_locked && <span aria-label="locked">🔒</span>}
        {slot.is_user_swapped && <span aria-label="swapped" className="text-xs text-blue-600">swapped</span>}
        <span>Exercise #{slot.exercise_id}</span>
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-700">
        <span>{slot.sets} × {slot.reps}{slot.load != null ? ` @ ${slot.load}` : ''}</span>
        {slot.note && <span className="text-amber-600">{slot.note}</span>}
        <SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={onSwap} />
      </div>
    </div>
  );
}
```
> `Exercise #{id}` is a placeholder label until the preview payload carries exercise names; if the backend is extended to include `exercise_name` on `SlotPreview`, render that instead. (Tracked in Plan 1 §13 notes — not required for MVP.)

```tsx
// frontend/src/components/SessionCard.tsx
import { Card } from './Card';
import { SlotRow } from './SlotRow';
import type { FeedbackAction, WorkoutPreview } from '@/types/program';

export function SessionCard({ workout, onAction, onSwap }: {
  workout: WorkoutPreview; onAction: (a: FeedbackAction) => void; onSwap: (weId: number) => void;
}) {
  return (
    <Card>
      <h3 className="font-semibold mb-2">{workout.name}</h3>
      {workout.slots.map((s) => (
        <SlotRow key={s.workout_exercise_id} slot={s} onAction={onAction} onSwap={() => onSwap(s.workout_exercise_id)} />
      ))}
    </Card>
  );
}
```

```tsx
// frontend/src/components/WeekTabs.tsx
export function WeekTabs({ weeks, active, onSelect }: {
  weeks: number[]; active: number; onSelect: (w: number) => void;
}) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto border-b mb-4">
      {weeks.map((w) => (
        <button key={w} role="tab" aria-selected={w === active} onClick={() => onSelect(w)}
          className={`px-3 py-2 whitespace-nowrap ${w === active ? 'border-b-2 border-blue-600 font-semibold' : 'text-gray-500'}`}>
          Week {w}
        </button>
      ))}
    </div>
  );
}
```

```tsx
// frontend/src/components/ExerciseAlternativesModal.tsx
import { useSlotAlternatives } from '@/hooks/usePrograms';

export function ExerciseAlternativesModal({ programId, weId, onPick, onClose }: {
  programId: number; weId: number; onPick: (exerciseId: number) => void; onClose: () => void;
}) {
  const { data, isLoading } = useSlotAlternatives(programId, weId, true);
  return (
    <div role="dialog" aria-label="Swap exercise" className="fixed inset-0 bg-black/40 flex items-center justify-center z-20">
      <div className="bg-white rounded-lg p-4 w-80 max-h-[70vh] overflow-y-auto">
        <div className="flex justify-between mb-2">
          <h4 className="font-semibold">Swap exercise</h4>
          <button aria-label="close" onClick={onClose}>✕</button>
        </div>
        {isLoading ? <p>Loading…</p> : (data ?? []).map((a) => (
          <button key={a.id} className="block w-full text-left px-2 py-2 hover:bg-gray-50" onClick={() => onPick(a.id)}>{a.name}</button>
        ))}
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/components/DraftProgramView.tsx
import { useState } from 'react';
import { WeekTabs } from './WeekTabs';
import { SessionCard } from './SessionCard';
import { ExerciseAlternativesModal } from './ExerciseAlternativesModal';
import { useSubmitFeedback } from '@/hooks/usePrograms';
import type { FeedbackAction, ProgramPreview } from '@/types/program';

export function DraftProgramView({ program, programId }: { program: ProgramPreview; programId: number }) {
  const weeks = Object.keys(program.weeks).map(Number).sort((a, b) => a - b);
  const [active, setActive] = useState(weeks[0] ?? 1);
  const [swapFor, setSwapFor] = useState<number | null>(null);
  const feedback = useSubmitFeedback(programId);
  const onAction = (a: FeedbackAction) => feedback.mutate(a);
  return (
    <div>
      <WeekTabs weeks={weeks} active={active} onSelect={setActive} />
      <div className="space-y-4">
        {(program.weeks[String(active)] ?? []).map((w) => (
          <SessionCard key={w.workout_id} workout={w} onAction={onAction} onSwap={setSwapFor} />
        ))}
      </div>
      {swapFor != null && (
        <ExerciseAlternativesModal programId={programId} weId={swapFor}
          onPick={(exerciseId) => { onAction({ type: 'swap', workout_exercise_id: swapFor, exercise_id: exerciseId }); setSwapFor(null); }}
          onClose={() => setSwapFor(null)} />
      )}
    </div>
  );
}
```
Export all six from `src/components/index.ts`.

- [ ] **Step 5: Run both test files → PASS.**

- [ ] **Step 6: Commit** — `git commit -m "feat(program-ui): draft review + feedback components"`

---

### Task 7: Builder page (wizard) + routes

**Files:**
- Create: `frontend/src/pages/ProgramBuilderPage.tsx`, `frontend/src/components/Stepper.tsx`
- Modify: `frontend/src/App.tsx` (add routes), `frontend/src/components/index.ts`
- Test: `frontend/src/tests/pages/ProgramBuilderPage.test.tsx`

**Interfaces:**
- Consumes: `ProgramCreationForm`, `TemplateMatchList`, `RequiredInputsForm`, `DraftProgramView`, all hooks.
- Produces: `/programs/new` wizard; steps `preferences → select → inputs → review`.

- [ ] **Step 1: Write the failing test (step gating: match → select)**

```tsx
// frontend/src/tests/pages/ProgramBuilderPage.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProgramBuilderPage from '@/pages/ProgramBuilderPage';

const match = { template_id: 1, slug: 'fb', name: 'Full Body', fit_pct: 90, factors: {}, required_inputs: [] };
vi.mock('@/hooks/usePrograms', () => ({
  useMatchTemplates: () => ({ mutate: (_: unknown, o: any) => o.onSuccess([match]), data: [match], isPending: false }),
  useCreateDraft: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useProgramPreview: () => ({ data: undefined }),
  useSubmitFeedback: () => ({ mutate: vi.fn() }),
  useAcceptProgram: () => ({ mutateAsync: vi.fn() }),
  useSlotAlternatives: () => ({ data: [] }),
  programKeys: { preview: (id: number) => ['program', id] },
}));
// Stub ProgramCreationForm to immediately submit valid preferences
vi.mock('@/components/ProgramCreationForm', () => ({
  ProgramCreationForm: ({ onSubmit }: any) => (
    <button onClick={() => onSubmit({ environment_id: 1, days_per_week: 3, session_duration_min: 60, fitness_focus: 'strength', weight_unit: 'kg', duration_weeks: 8 })}>go</button>
  ),
}));

function wrap(ui: React.ReactNode) {
  return <MemoryRouter><QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider></MemoryRouter>;
}

it('advances from preferences to template selection', async () => {
  render(wrap(<ProgramBuilderPage />));
  await userEvent.click(screen.getByText('go'));
  expect(await screen.findByText('Full Body')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement the Stepper + page**

```tsx
// frontend/src/components/Stepper.tsx
export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="flex gap-2 mb-6 text-sm">
      {steps.map((label, i) => (
        <li key={label} className={`px-2 py-1 rounded ${i === current ? 'bg-blue-600 text-white' : i < current ? 'text-blue-600' : 'text-gray-400'}`}>
          {i + 1}. {label}
        </li>
      ))}
    </ol>
  );
}
```

```tsx
// frontend/src/pages/ProgramBuilderPage.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Stepper, TemplateMatchList, RequiredInputsForm, DraftProgramView, Button } from '@/components';
import { ProgramCreationForm } from '@/components/ProgramCreationForm';
import { useAcceptProgram, useCreateDraft, useMatchTemplates } from '@/hooks/usePrograms';
import type { MatchRequest, ProgramPreview, TemplateMatch } from '@/types/program';

const STEPS = ['Preferences', 'Select', 'Details', 'Review'];

export default function ProgramBuilderPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [prefs, setPrefs] = useState<MatchRequest | null>(null);
  const [chosen, setChosen] = useState<TemplateMatch | null>(null);
  const [draft, setDraft] = useState<ProgramPreview | null>(null);

  const match = useMatchTemplates();
  const createDraft = useCreateDraft();
  const accept = useAcceptProgram(draft?.program_id ?? 0);

  const onPrefs = (values: MatchRequest) => {
    setPrefs(values);
    match.mutate(values, { onSuccess: () => setStep(1) });
  };

  const onPick = (m: TemplateMatch) => {
    setChosen(m);
    if (m.required_inputs.length > 0) { setStep(2); return; }
    void makeDraft(m, {});
  };

  const makeDraft = async (m: TemplateMatch, requiredInputs: Record<string, number | string>) => {
    if (!prefs) return;
    const program = await createDraft.mutateAsync({ ...prefs, template_id: m.template_id, required_inputs: requiredInputs });
    setDraft(program);
    setStep(3);
  };

  const onAccept = async () => {
    const accepted = await accept.mutateAsync();
    navigate(`/programs/${accepted.program_id}`);
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <Stepper steps={STEPS} current={step} />
      {step === 0 && <ProgramCreationForm onSubmit={onPrefs} />}
      {step === 1 && <TemplateMatchList matches={match.data ?? []} selectedId={chosen?.template_id ?? null} onSelect={onPick} />}
      {step === 2 && chosen && <RequiredInputsForm inputs={chosen.required_inputs} onSubmit={(v) => makeDraft(chosen, v)} />}
      {step === 3 && draft && (
        <div>
          <DraftProgramView program={draft} programId={draft.program_id} />
          <div className="mt-6 flex justify-end">
            <Button onClick={onAccept}>Accept program</Button>
          </div>
        </div>
      )}
    </div>
  );
}
```
> `ProgramCreationForm.onSubmit` must yield a `MatchRequest`-shaped object. Read `src/components/ProgramCreationForm.tsx` + `src/types/programCreation.ts`; add an adapter if its payload differs (map its fields → `MatchRequest`). Keep backward compatibility with its existing usage.

- [ ] **Step 4: Check ProgramCreationForm integration**

Before wiring the page: `ProgramCreationForm` is now refactored (Task 0) to require an `onSubmit` callback and to output `MatchRequest`-shaped values directly (environment_id, days_per_week, session_duration_min, weight_unit, duration_weeks). Verify its new prop signature and run `docker-compose exec frontend npm run test -- ProgramCreationForm.test.tsx` to confirm the form is ready.

- [ ] **Step 5: Add routes to `App.tsx`**

```tsx
// add imports
import ProgramBuilderPage from '@/pages/ProgramBuilderPage';
import ProgramPreviewPage from '@/pages/ProgramPreviewPage';   // Task 8
import ProgramsListPage from '@/pages/ProgramsListPage';       // Task 8
// add inside the authenticated <Routes> block, before the catch-all:
<Route path="/programs" element={<ProgramsListPage />} />
<Route path="/programs/new" element={<ProgramBuilderPage />} />
<Route path="/programs/:id" element={<ProgramPreviewPage />} />
```

- [ ] **Step 6: Run tests → PASS.** (Routes referencing Task 8 pages will compile once Task 8 lands; if executing strictly in order, stub the two imports as empty components first, then implement in Task 8.)

- [ ] **Step 7: Commit** — `git commit -m "feat(program-ui): builder wizard page + routes"`

---

### Task 8: Programs list + read-only preview pages

**Files:**
- Create: `frontend/src/pages/ProgramsListPage.tsx`, `frontend/src/pages/ProgramPreviewPage.tsx`, `frontend/src/components/ProgramListCard.tsx`
- Modify: `frontend/src/components/index.ts`
- Test: `frontend/src/tests/pages/ProgramPreviewPage.test.tsx`

**Interfaces:**
- Consumes: `useProgramPreview`, `getProgramPreview`.
- Produces: `/programs` list, `/programs/:id` read-only preview (reuses `WeekTabs` + `SessionCard` in read-only mode — feedback menu hidden when `status !== 'draft'`).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/tests/pages/ProgramPreviewPage.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProgramPreviewPage from '@/pages/ProgramPreviewPage';

vi.mock('@/hooks/usePrograms', () => ({
  useProgramPreview: () => ({
    data: { program_id: 1, name: 'My Program', status: 'active', duration_weeks: 1,
      weeks: { '1': [{ workout_id: 1, key: 'a', name: 'Day A', slots: [] }] } },
    isLoading: false,
  }),
}));

it('renders an accepted program read-only', () => {
  render(
    <MemoryRouter initialEntries={['/programs/1']}>
      <QueryClientProvider client={new QueryClient()}>
        <Routes><Route path="/programs/:id" element={<ProgramPreviewPage />} /></Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  expect(screen.getByText('My Program')).toBeInTheDocument();
  expect(screen.getByText('Day A')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement (`ProgramPreviewPage` reuses read-only session rendering)**

```tsx
// frontend/src/pages/ProgramPreviewPage.tsx
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Spinner, WeekTabs } from '@/components';
import { useProgramPreview } from '@/hooks/usePrograms';

export default function ProgramPreviewPage() {
  const { id } = useParams();
  const programId = Number(id);
  const { data, isLoading } = useProgramPreview(programId);
  const [active, setActive] = useState(1);
  if (isLoading || !data) return <Spinner />;
  const weeks = Object.keys(data.weeks).map(Number).sort((a, b) => a - b);
  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">{data.name}</h1>
      <WeekTabs weeks={weeks} active={active} onSelect={setActive} />
      <div className="space-y-4">
        {(data.weeks[String(active)] ?? []).map((w) => (
          <Card key={w.workout_id}>
            <h3 className="font-semibold mb-2">{w.name}</h3>
            {w.slots.map((s) => (
              <div key={s.workout_exercise_id} className="flex justify-between py-1 text-sm">
                <span>Exercise #{s.exercise_id}{s.is_locked ? ' 🔒' : ''}</span>
                <span>{s.sets} × {s.reps}{s.load != null ? ` @ ${s.load}` : ''}{s.note ? ` (${s.note})` : ''}</span>
              </div>
            ))}
          </Card>
        ))}
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/pages/ProgramsListPage.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components';

export default function ProgramsListPage() {
  // MVP: link to the builder; a GET /user/programs list endpoint can populate this later.
  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Your programs</h1>
        <Link to="/programs/new"><Button>Create program</Button></Link>
      </div>
      <p className="text-gray-500">Create your first program to get started.</p>
    </div>
  );
}
```
> `ProgramsListPage` is intentionally minimal for MVP (no list endpoint in Plan 1). When a `GET /user/programs` endpoint exists, render `ProgramListCard`s from it. `ProgramListCard` can be created now as a presentational component and wired later. Note: `EnvironmentsPage` also updated in Task 0 — its "Generate Program" action now navigates to `/programs/new` instead of embedding `ProgramCreationForm`.

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Full quality gate**

```bash
docker-compose exec frontend npm run test
docker-compose exec frontend npm run lint -- --fix
docker-compose exec frontend npm run type-check
```
Expected: all green.

- [ ] **Step 6: Commit** — `git commit -m "feat(program-ui): programs list + read-only preview pages"`

---

## Self-Review (frontend)

- **Spec §11 coverage:** routes → Task 7,8. Wizard steps 1–5 → Task 7 (preferences/select/inputs/review/accept). Components → Tasks 4–8. State & API → Tasks 2,3. Types → Task 1. Testing → every task is Vitest+RTL.
- **Type consistency:** `MatchRequest`/`DraftRequest`/`ProgramPreview`/`FeedbackAction`/`TemplateMatch` used identically across api (Task 2), hooks (Task 3), and pages (Tasks 7,8).
- **Known verification points for the implementer:** `ProgramCreationForm` payload shape → adapter to `MatchRequest` (Task 7); `FormField` prop names (Task 5); presence of `QueryClientProvider` (Task 3); slot exercise *names* not yet in the preview payload — rendered as `Exercise #id` until Plan 1 optionally adds `exercise_name`.
