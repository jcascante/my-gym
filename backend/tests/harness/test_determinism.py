"""Property test: byte-identical determinism (plan Section 1.8).

Run the SAME profile through the SAME formula twice and compare serialized drafts --
`rank_templates`/`build_draft` are pure/sync functions over immutable inputs, so two
runs of the same profile under the same `EngineConfig` must pick the identical
top-ranked template and produce an identical per-exercise draft fingerprint.

Genuine failure mode this would catch: any hidden nondeterminism -- iterating over an
unordered `set`/`dict` in a way that leaks into tie-breaking, relying on wall-clock or
random tie-breaks, or a beam-search prune that isn't a total order (see `assembly.py`'s
`sorted(..., key=lambda b: (-b.objective, b._latest_exercise_id()))`, whose tie-break
key exists specifically to avoid this).
"""

from __future__ import annotations

from app.models import Exercise, ProgramTemplate
from tests.harness.profiles import SyntheticProfile
from tests.harness.runner import ProfileResult, build_definitions, run_profile


def test_same_profile_same_formula_twice_is_byte_identical(
    catalog_templates: list[ProgramTemplate],
    catalog_exercises: list[Exercise],
    bounded_grid: list[SyntheticProfile],
    grid_results: list[ProfileResult],
) -> None:
    """First pass comes from the shared `grid_results` fixture; this test performs a
    completely independent second pass over the same grid and asserts every field
    that should be reproducible (top template, advisory flag, draft fingerprint)
    matches exactly, for both the old and new formula."""
    definitions = build_definitions(catalog_templates)
    second_pass = [run_profile(profile, catalog_templates, catalog_exercises, definitions) for profile in bounded_grid]

    assert len(second_pass) == len(grid_results)
    for first, second in zip(grid_results, second_pass):
        assert first.profile == second.profile

        assert first.old.top_template_slug == second.old.top_template_slug
        assert first.old.all_infeasible == second.old.all_infeasible
        assert first.old.draft_fingerprint == second.old.draft_fingerprint

        assert first.new.top_template_slug == second.new.top_template_slug
        assert first.new.all_infeasible == second.new.all_infeasible
        assert first.new.draft_fingerprint == second.new.draft_fingerprint
