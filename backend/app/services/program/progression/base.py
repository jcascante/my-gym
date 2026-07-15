from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SlotBase:
    sets: int
    reps_min: int
    reps_max: int
    rest_seconds: int
    base_load: float | None


@dataclass(frozen=True)
class SetScheme:
    sets: int
    reps: int
    load: float | None
    rest_seconds: int
    note: str | None = None


class ProgressionModel(Protocol):
    key: str

    def resolve(self, base: SlotBase, week: int, params: dict[str, object]) -> SetScheme: ...


_REGISTRY: dict[str, ProgressionModel] = {}


def register(model: ProgressionModel) -> None:
    _REGISTRY[model.key] = model


def get_model(key: str) -> ProgressionModel:
    if key not in _REGISTRY:
        raise KeyError(f"Unknown progression model: {key}")
    return _REGISTRY[key]
