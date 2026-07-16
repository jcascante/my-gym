from typing import cast

from app.services.program.progression.base import SetScheme, SlotBase, register


class LinearLoad:
    key = "linear_load"

    def resolve(self, base: SlotBase, week: int, params: dict[str, object]) -> SetScheme:
        increment = float(cast(float, params.get("increment", 2.5)))
        load = None if base.base_load is None else base.base_load + increment * (week - 1)
        return SetScheme(sets=base.sets, reps=base.reps_min, load=load, rest_seconds=base.rest_seconds)


register(LinearLoad())
