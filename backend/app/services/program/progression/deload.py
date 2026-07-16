from app.services.program.progression.base import SetScheme


def apply_deload(scheme: SetScheme, week: int, every: int | None, factor: float = 0.6) -> SetScheme:
    if not every or week % every != 0 or scheme.load is None:
        return scheme
    return SetScheme(
        sets=scheme.sets,
        reps=scheme.reps,
        load=round(scheme.load * factor, 2),
        rest_seconds=scheme.rest_seconds,
        note="deload",
    )
