import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


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


def get_model(key: str, version: str | None = None) -> ProgressionModel:
    """Look up a registered progression model, optionally version-pinned.

    A `version` first tries the versioned key `f"{key}@{version}"` (Task 4.5:
    template/model versioning), falling back to the bare `key` when no such
    version has been registered -- today every model is only ever registered
    under its bare key, so passing a version is a safe no-op until a future
    model change registers a distinct `key@version` entry to preserve older
    programs' pinned behavior.
    """
    if version:
        versioned_key = f"{key}@{version}"
        if versioned_key in _REGISTRY:
            return _REGISTRY[versioned_key]
        logger.warning(f"Model version {key}@{version} not found, falling back to current")
    if key not in _REGISTRY:
        raise KeyError(f"Unknown progression model: {key}")
    return _REGISTRY[key]
