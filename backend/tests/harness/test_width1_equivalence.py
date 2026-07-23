"""Property test: width=1 beam search reproduces greedy `build_draft` output exactly,
swept across the bounded synthetic-profile grid using the real seeded catalog (plan
Section 1.8, design decision #5).

Task 5 (`test_drafting.py::test_beam_width_1_reproduces_greedy_output_exactly`) already
covers this for one hand-picked fixture. This test verifies the same property but swept
across ~250 profiles -- that breadth (different templates, equipment, injuries, and
resulting slot-candidate pools) is the value this harness task adds over Task 5's
single-fixture check.

Template selection is pinned to the legacy ranking (`config=None`) for both drafts, so
only the drafting/assembly strategy differs between the two calls being compared --
`WIDTH_ONE_CONFIG` deliberately leaves `use_constraint_scorer` off (see `runner.py`), so
ranking is identical to `config=None` regardless, but pinning it explicitly keeps this
test from silently starting to compare drafts of two DIFFERENT top-ranked templates if
that assumption ever changes.

Genuine failure mode this would catch: `assemble_session`'s width=1 beam picking a
different exercise than greedy's `ranked[0]` for some slot -- e.g. a tie-break or
candidate-pool ordering divergence that only shows up for certain equipment/injury
combinations, which a single fixture can't surface.
"""

from __future__ import annotations

from app.models import Exercise, ProgramTemplate
from tests.harness.profiles import SyntheticProfile
from tests.harness.runner import (
    WIDTH_ONE_CONFIG,
    build_definitions,
    build_feasibility,
    draft_fingerprint,
    draft_for,
    equipment_for,
    rank,
)


def test_width1_beam_matches_greedy_across_grid(
    catalog_templates: list[ProgramTemplate],
    catalog_exercises: list[Exercise],
    bounded_grid: list[SyntheticProfile],
) -> None:
    definitions = build_definitions(catalog_templates)
    mismatches: list[tuple[SyntheticProfile, str]] = []

    for profile in bounded_grid:
        equipment = equipment_for(profile)
        feasibility = build_feasibility(catalog_templates, catalog_exercises, definitions, equipment)

        ranked_legacy = rank(profile, catalog_templates, catalog_exercises, definitions, feasibility, config=None)
        ranked_width1 = rank(
            profile, catalog_templates, catalog_exercises, definitions, feasibility, config=WIDTH_ONE_CONFIG
        )
        # Precondition this test relies on: width=1's config leaves the constraint
        # scorer off, so template ranking must agree with the legacy path.
        assert ranked_legacy[0].template_id == ranked_width1[0].template_id

        top = ranked_legacy[0]
        template = next(t for t in catalog_templates if t.id == top.template_id)
        definition = definitions[top.template_id]

        greedy_program = draft_for(profile, template, definition, catalog_exercises, config=None)
        beam_program = draft_for(profile, template, definition, catalog_exercises, config=WIDTH_ONE_CONFIG)

        greedy_fp = draft_fingerprint(greedy_program)
        beam_fp = draft_fingerprint(beam_program)
        if greedy_fp != beam_fp:
            mismatches.append((profile, top.slug))

    assert not mismatches, f"width=1 beam diverged from greedy for {len(mismatches)} profile(s): {mismatches[:5]}"
