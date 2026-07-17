from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class SchemeDef(BaseModel):
    sets: int
    reps_min: int
    reps_max: int
    rest_seconds: int
    target_rpe: float | None = None
    intensity_pct: float | None = None


class SlotRule(BaseModel):
    pattern: str | None = None
    region: str | None = None
    muscles: list[str] = []
    priority: str = "secondary"  # primary | secondary | accessory
    scheme: str = "accessory"

    @model_validator(mode="after")
    def _require_pattern_or_region(self) -> "SlotRule":
        if not self.pattern and not self.region:
            raise ValueError("slot must define either pattern or region")
        return self


class SessionDef(BaseModel):
    key: str
    name: str
    order: int
    slots: list[SlotRule]


class SplitDef(BaseModel):
    sessions: list[SessionDef]


class ProgressionRef(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_key: str
    params: dict[str, Any] = {}
    deload_every: int | None = None  # None = no deload modifier


class RequiredInput(BaseModel):
    key: str
    label: str
    type: str = "number"  # number | text
    applies_to: str | None = None  # movement_slug or slot key the value seeds


class TemplateDefinition(BaseModel):
    split: SplitDef
    progression: ProgressionRef
    schemes: dict[str, SchemeDef]
    required_inputs: list[RequiredInput] = []

    @classmethod
    def from_orm_template(cls, t: Any) -> "TemplateDefinition":
        split_data = dict(t.split)
        schemes = split_data.pop("schemes", {})
        return cls(
            split=SplitDef(**split_data),
            progression=ProgressionRef(**t.progression_ref),
            schemes={k: SchemeDef(**v) for k, v in schemes.items()},
            required_inputs=[RequiredInput(**r) for r in t.required_inputs],
        )
