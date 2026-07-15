# Program Generation Engine — Documentation Implementation Plan (Plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the program-generation engine in the project's GitHub-Pages-style HTML docs — a **technical** doc and a **user** doc — and wire them into the existing navigation, per the `documentation` skill.

**Architecture:** Docs are standalone self-contained HTML files under `docs/technical/` and `docs/user/`, each with inline CSS matching the existing files, linked from `docs/technical/index.html`, `docs/index.html`, and the user index nav.

**Tech Stack:** Hand-written HTML/CSS, mirroring `docs/technical/EXERCISE_LIBRARY_TECHNICAL.html` and `docs/user/EXERCISE_LIBRARY.html`.

## Global Constraints

- Match the visual style and structure of the **existing** technical/user docs exactly (same header, container, CSS variables/colors). Copy an existing file's `<style>` block rather than inventing new styling.
- Content source of truth: `docs/superpowers/specs/2026-07-15-program-generation-engine-design.md`.
- No external assets (self-contained HTML). Relative links only.
- Commit after each doc is complete and linked.

---

### Task 1: Technical documentation page

**Files:**
- Create: `docs/technical/PROGRAM_GENERATION_TECHNICAL.html`
- Reference (read first, copy structure/CSS): `docs/technical/EXERCISE_LIBRARY_TECHNICAL.html`

**Interfaces:** none (static doc).

- [ ] **Step 1: Copy the shell**

Read `docs/technical/EXERCISE_LIBRARY_TECHNICAL.html`, copy its `<head>`/`<style>`/header/container scaffold into the new file, and change the `<title>` to `Program Generation Engine - Technical Documentation` and the header `<h1>` to match.

- [ ] **Step 2: Author the body sections**

Include these sections (content drawn verbatim/condensed from the spec — no placeholders):

1. **Overview** — rules-based, deterministic, <100 ms; LLM-ready seam; base-week + derive.
2. **Layered template model** — Split + Slot rules + Progression reference; include the YAML-style example from spec §2 inside a `<pre><code>` block.
3. **Data model** — an HTML `<table>` of the four tables (`program_templates`, `workout_programs`, `workouts`, `workout_exercises`) and key columns (from spec §4). Include the `constraints` JSON example in a `<pre>`.
4. **Progression models** — table of `linear_load`, `double_progression`, `weekly_undulating`, `deload` with behavior (spec §3). State that algorithms live in code, config in the DB.
5. **Matching algorithm** — the weighted-factor table (spec §5) and the top-3 output shape.
6. **Exercise selection** — filter/rank/fallback pipeline (spec §6).
7. **Feedback & re-adaptation** — constraints-overlay model; the action table (spec §7).
8. **API endpoints** — a table mapping each endpoint to method + purpose (spec §8), noting request/response schema names from Plan 1 `program_api.py`.
9. **Services layout** — the `app/services/program/` tree (spec §9).
10. **Testing & performance** — TDD, golden-file snapshots, latency (spec §10).
11. **Template authoring roadmap** — MVP seeded catalog now; form builder + LLM-assisted authoring + ownership deferred (spec §12).

- [ ] **Step 3: Verify it renders and has no broken internal anchors**

Run: `python3 -m http.server -d docs 8080 &` then open `http://localhost:8080/technical/PROGRAM_GENERATION_TECHNICAL.html`.
Expected: styled page, all sections present, no console errors. Stop the server afterward (`kill %1`).

- [ ] **Step 4: Commit**

```bash
git add docs/technical/PROGRAM_GENERATION_TECHNICAL.html
git commit -m "docs: technical documentation for program generation engine"
```

---

### Task 2: User documentation page

**Files:**
- Create: `docs/user/PROGRAM_BUILDER.html`
- Reference (read first, copy structure/CSS): `docs/user/EXERCISE_LIBRARY.html`

**Interfaces:** none (static doc).

- [ ] **Step 1: Copy the shell**

Read `docs/user/EXERCISE_LIBRARY.html`; copy its scaffold/CSS. Set `<title>` to `Building Your Program - MyGym` and header accordingly.

- [ ] **Step 2: Author the body (task-oriented, non-technical)**

Sections, written for an end user (no schema/jargon):

1. **What the builder does** — answers a few questions, suggests matching programs, you fine-tune, then save.
2. **Step 1 — Your preferences** — choose environment, days/week, session length, focus.
3. **Step 2 — Pick a program** — the shortlist with fit % and why each fits; pick the one you like.
4. **Step 3 — A couple of details** — enter starting weights if asked.
5. **Step 4 — Review & adjust** — browse weeks; per exercise you can **swap**, **exclude / get another**, **adjust volume**, or **lock** ones you like so re-adjustments never change them. Explain the 🔒 badge.
6. **Step 5 — Accept & preview** — save it; view your program any time.
7. **Tips** — what "deload week" means; why some exercises were chosen (equipment/injuries).

Keep paragraphs short; use `<ol>`/`<ul>` and callout boxes consistent with the existing user docs.

- [ ] **Step 3: Verify rendering** (same local-server check as Task 1, `http://localhost:8080/user/PROGRAM_BUILDER.html`).

- [ ] **Step 4: Commit**

```bash
git add docs/user/PROGRAM_BUILDER.html
git commit -m "docs: user guide for the program builder"
```

---

### Task 3: Wire both docs into navigation

**Files:**
- Modify: `docs/technical/index.html`, `docs/index.html`, and the user docs index (the file listing user guides — confirm which of `docs/index.html` or a `docs/user/index.html` serves that role by reading them).
- Reference: existing nav entries for the Exercise Library in each index.

**Interfaces:** none.

- [ ] **Step 1: Find the existing nav pattern**

Run: `grep -rn "EXERCISE_LIBRARY" docs/*.html docs/technical/index.html`
Note the exact markup used to link the Exercise Library doc in each index.

- [ ] **Step 2: Add a technical nav entry**

In `docs/technical/index.html`, duplicate the Exercise Library link block and point it at `PROGRAM_GENERATION_TECHNICAL.html` with title "Program Generation Engine" and a one-line description.

- [ ] **Step 3: Add a user nav entry**

In the user-facing index (`docs/index.html` and/or the user index), duplicate the Exercise Library user-guide link and point it at `user/PROGRAM_BUILDER.html` titled "Building Your Program".

- [ ] **Step 4: Verify all links resolve**

Run: `python3 -m http.server -d docs 8080 &`; from `http://localhost:8080/` and `http://localhost:8080/technical/index.html`, click through to both new pages. Expected: no 404s. `kill %1` when done.

- [ ] **Step 5: Commit**

```bash
git add docs/index.html docs/technical/index.html
git commit -m "docs: link program generation docs into navigation"
```

---

## Self-Review (docs)

- **Spec coverage:** technical doc covers spec §§1–10, 12; user doc covers the §8/§11 flow in plain language; nav wiring makes both discoverable. No section of the spec intended for documentation is left unpublished.
- **Placeholder scan:** each task specifies concrete section content sourced from named spec sections — no "TBD".
- **Consistency:** both pages reuse an existing file's CSS shell, so styling matches; nav entries mirror the Exercise Library pattern already in the indexes.
- **Known verification point for the implementer:** confirm which index file serves the user-facing guide list (Task 3 Step 1) before editing.
