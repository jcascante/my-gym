"""Property test: p95 generation latency < 100ms, plus the report-generation artifact
(plan Section 1.8, design decisions #3 and #4).

Latency is measured by `runner.run_formula` around just the `rank_templates` +
`build_draft` calls (not fixture/DB setup); `grid_results` (session-scoped, computed
once) supplies the full bounded-grid timings for both formulas.
"""

from __future__ import annotations

from pathlib import Path

from tests.harness.report import generate_report, render_report_markdown
from tests.harness.runner import ProfileResult

_REPORT_PATH = Path(__file__).parent / "latest_report.md"


def test_p95_latency_under_100ms(grid_results: list[ProfileResult]) -> None:
    """Genuine failure mode: a regression that makes ranking/drafting scan the full
    exercise pool per slot without the existing filtering short-circuits, or a beam
    search with an unbounded width, would push p95 well past 100ms."""
    report = generate_report(grid_results)
    assert report.total_profiles == len(grid_results)
    assert report.latency_p95_old_ms < 100.0, f"old formula p95={report.latency_p95_old_ms:.3f}ms"
    assert report.latency_p95_new_ms < 100.0, f"new formula p95={report.latency_p95_new_ms:.3f}ms"


def test_report_generation_writes_artifact(grid_results: list[ProfileResult]) -> None:
    """Writing `latest_report.md` is a side effect of running the harness (satisfies the
    plan's "harness comparison report generated" Phase 1 exit criterion) -- not itself
    an assertion. The acceptance-criteria numbers are asserted in dedicated tests
    (determinism, goal-mismatch, width=1, p95 latency) elsewhere in this package."""
    report = generate_report(grid_results)
    rendered = render_report_markdown(report)

    _REPORT_PATH.write_text(rendered)

    assert _REPORT_PATH.exists()
    assert _REPORT_PATH.read_text() == rendered
    # Sanity bounds on the reported rates -- not acceptance criteria, just guards
    # against a broken percentage computation (e.g. counting past n or dividing by 0).
    assert 0.0 <= report.rank_agreement <= 1.0
    assert 0.0 <= report.advisory_rate_old <= 1.0
    assert 0.0 <= report.advisory_rate_new <= 1.0
