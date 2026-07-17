from typing import Any

VARIETY_POOL_SIZE: dict[str, int] = {"low": 1, "medium": 2, "high": 3}


def pool_size_for(variety_preference: str) -> int:
    return VARIETY_POOL_SIZE.get(variety_preference, 1)


def rotation_pool_ids(ranked: list[Any], n: int) -> list[int]:
    return [ex.id for ex in ranked[:n]]
