# Synthetic-user A/B harness report

Old formula: `config=None` (legacy `HeuristicTemplateScorer` + greedy drafting).
New formula: `EngineConfig(flags.use_constraint_scorer=True, flags.use_beam_search=True, assembly.beam_width=4)`.

- Profiles evaluated: 250
- Rank agreement (old top template == new top template): 78.0%
- Advisory rate (all_infeasible), old formula: 0.0%
- Advisory rate (all_infeasible), new formula: 0.0%
- Latency p95, old formula: 8.691 ms
- Latency p95, new formula: 20.685 ms
