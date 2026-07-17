from collections import Counter


def coverage_deficit(muscles: list[str], coverage: "Counter[str]") -> float:
    if not muscles:
        return 0.5
    mean_cov = sum(coverage[m] for m in muscles) / len(muscles)
    max_cov = max(coverage.values(), default=0)
    return 1 - mean_cov / (1 + max_cov)
