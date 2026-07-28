"""Template/model version pinning for deterministic program generation (Phase 4, Task 4.5).

`WorkoutProgram.model_version` / `ranking_weights_version` pin, at generation time,
which progression-pipeline version and exercise-substitution-ranking weights artifact
produced a program's prescriptions. Re-deriving a week for the same program later must
keep using these pinned values, not whatever is "current" at read time -- otherwise a
live model or weights bump would silently reshuffle historical prescriptions. Existing
programs predating these columns have both fields `None`; callers fall back to the
current/live versions for them (`resolve_program_versions` below), which is a change in
behavior only in the sense that it's the first time these programs get a value at all.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.constants import CURRENT_PROGRESSION_MODEL_VERSION, DEFAULT_RANKING_WEIGHTS_VERSION

if TYPE_CHECKING:
    from app.models.program import WorkoutProgram

logger = logging.getLogger(__name__)

# backend/app/services/program/versioning.py -> backend/data/exercise_substitution_weights.json
DEFAULT_RANKING_WEIGHTS_PATH = Path(__file__).resolve().parents[3] / "data" / "exercise_substitution_weights.json"


def get_current_model_version() -> str:
    """The progression-pipeline logic version stamped onto newly generated programs."""
    return CURRENT_PROGRESSION_MODEL_VERSION


def get_current_ranking_weights_version(path: Path | None = None) -> str:
    """Read the trained weights artifact's `_metadata.weights_version`.

    Falls back to `DEFAULT_RANKING_WEIGHTS_VERSION` when the artifact is missing,
    unreadable, or predates the `_metadata` field (a pre-4.5 or not-yet-trained
    artifact) -- a missing/malformed artifact must never block program generation.
    """
    weights_path = path or DEFAULT_RANKING_WEIGHTS_PATH
    try:
        payload = json.loads(weights_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "Could not read ranking weights artifact at %s (%s); using default version %r.",
            weights_path,
            exc,
            DEFAULT_RANKING_WEIGHTS_VERSION,
        )
        return DEFAULT_RANKING_WEIGHTS_VERSION

    metadata = payload.get("_metadata") if isinstance(payload, dict) else None
    if not isinstance(metadata, dict):
        return DEFAULT_RANKING_WEIGHTS_VERSION
    version = metadata.get("weights_version")
    return str(version) if version else DEFAULT_RANKING_WEIGHTS_VERSION


def resolve_program_versions(
    program: "WorkoutProgram | None" = None,
    *,
    model_version: str | None = None,
    ranking_weights_version: str | None = None,
    weights_path: Path | None = None,
) -> tuple[str, str]:
    """Resolve the effective (model_version, ranking_weights_version) pair.

    Precedence per field: an explicit keyword argument (a caller pinning a version
    directly) wins, then the program's own stored pin (set at generation time), then
    the current/live version -- covering both existing programs generated before
    these columns existed (stored values `None`) and brand-new generation (no
    `program` yet).
    """
    resolved_model_version = (
        model_version or (program.model_version if program is not None else None) or get_current_model_version()
    )
    resolved_ranking_weights_version = (
        ranking_weights_version
        or (program.ranking_weights_version if program is not None else None)
        or get_current_ranking_weights_version(weights_path)
    )
    return resolved_model_version, resolved_ranking_weights_version
