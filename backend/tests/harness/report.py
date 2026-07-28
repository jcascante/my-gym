"""Report generator for the A/B harness (plan Section 1.8, design decision #3).

Computes, across a list of `ProfileResult`s:
- rank agreement: fraction of profiles where old and new formula pick the same
  top-ranked template.
- advisory rate: fraction of profiles where `all_infeasible=True`, old vs new.
- latency p95: 95th percentile of the recorded per-profile match+draft timings, old vs
  new (a simple sorted-index percentile -- no new dependency needed).
"""

from __future__ import annotations

from dataclasses import dataclass

from tests.harness.runner import ProfileResult


@dataclass(frozen=True)
class HarnessReport:
    total_profiles: int
    rank_agreement: float
    advisory_rate_old: float
    advisory_rate_new: float
    latency_p95_old_ms: float
    latency_p95_new_ms: float


def _percentile(values: list[float], pct: float) -> float:
    """Simple sorted-index percentile (nearest-rank method)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round(pct * (len(ordered) - 1)))
    return ordered[idx]


def generate_report(results: list[ProfileResult]) -> HarnessReport:
    n = len(results)
    if n == 0:
        return HarnessReport(0, 0.0, 0.0, 0.0, 0.0, 0.0)

    rank_agreement = sum(1 for r in results if r.old.top_template_slug == r.new.top_template_slug) / n
    advisory_rate_old = sum(1 for r in results if r.old.all_infeasible) / n
    advisory_rate_new = sum(1 for r in results if r.new.all_infeasible) / n
    old_latencies_ms = [r.old.elapsed_seconds * 1000 for r in results]
    new_latencies_ms = [r.new.elapsed_seconds * 1000 for r in results]

    return HarnessReport(
        total_profiles=n,
        rank_agreement=rank_agreement,
        advisory_rate_old=advisory_rate_old,
        advisory_rate_new=advisory_rate_new,
        latency_p95_old_ms=_percentile(old_latencies_ms, 0.95),
        latency_p95_new_ms=_percentile(new_latencies_ms, 0.95),
    )


def render_report_markdown(report: HarnessReport) -> str:
    return (
        "# Synthetic-user A/B harness report\n\n"
        "Old formula: `config=None` (legacy `HeuristicTemplateScorer` + greedy drafting).\n"
        "New formula: `EngineConfig(flags.use_constraint_scorer=True, "
        "flags.use_beam_search=True, assembly.beam_width=4)`.\n\n"
        f"- Profiles evaluated: {report.total_profiles}\n"
        f"- Rank agreement (old top template == new top template): {report.rank_agreement:.1%}\n"
        f"- Advisory rate (all_infeasible), old formula: {report.advisory_rate_old:.1%}\n"
        f"- Advisory rate (all_infeasible), new formula: {report.advisory_rate_new:.1%}\n"
        f"- Latency p95, old formula: {report.latency_p95_old_ms:.3f} ms\n"
        f"- Latency p95, new formula: {report.latency_p95_new_ms:.3f} ms\n"
    )
