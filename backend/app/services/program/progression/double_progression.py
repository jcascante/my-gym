from typing import cast

from app.services.program.progression.base import SetScheme, SlotBase, register


class DoubleProgression:
    key = "double_progression"

    def resolve(self, base: SlotBase, week: int, params: dict[str, object]) -> SetScheme:
        increment = float(cast(float, params.get("increment", 2.5)))
        span = base.reps_max - base.reps_min + 1  # reps steps per load cycle
        step = week - 1
        cycle, offset = divmod(step, span)
        reps = base.reps_min + offset
        load = None if base.base_load is None else base.base_load + increment * cycle
        return SetScheme(sets=base.sets, reps=reps, load=load, rest_seconds=base.rest_seconds)


register(DoubleProgression())
