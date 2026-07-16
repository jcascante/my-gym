from typing import cast

from app.services.program.progression.base import SetScheme, SlotBase, register


class WeeklyUndulating:
    key = "weekly_undulating"

    def resolve(self, base: SlotBase, week: int, params: dict[str, object]) -> SetScheme:
        waves = cast(list[dict[str, object]], params.get("waves")) or [{"reps": base.reps_min, "intensity": 1.0}]
        increment = float(cast(float, params.get("increment", 0.0)))
        step = week - 1
        cycle, idx = divmod(step, len(waves))
        wave = waves[idx]
        if base.base_load is None:
            load = None
        else:
            load = base.base_load * float(cast(float, wave["intensity"])) + increment * cycle
        return SetScheme(
            sets=base.sets,
            reps=int(cast(int, wave["reps"])),
            load=load,
            rest_seconds=base.rest_seconds,
        )


register(WeeklyUndulating())
