from app.services.program.progression.base import SetScheme
from app.services.program.progression.ramp_guard import apply_ramp_guard, population_for


def test_population_for_prefers_post_amber_over_beginner():
    population = population_for(
        exercise_contraindications=["knee"],
        check_in_load_adjustments={"knee": {"load_pct": -0.15, "ledger_guard_pct": -0.30}},
        experience="beginner",
    )
    assert population == "post_amber"


def test_population_for_beginner_without_active_amber():
    population = population_for(
        exercise_contraindications=["knee"],
        check_in_load_adjustments={},
        experience="beginner",
    )
    assert population == "beginner"


def test_population_for_unrestricted_when_no_cap_applies():
    population = population_for(
        exercise_contraindications=[],
        check_in_load_adjustments={"knee": {}},
        experience="intermediate",
    )
    assert population == "unrestricted"


def test_apply_ramp_guard_unrestricted_never_caps():
    prior = SetScheme(sets=3, reps=5, load=100.0, rest_seconds=120)
    scheme = SetScheme(sets=5, reps=5, load=500.0, rest_seconds=120)
    assert apply_ramp_guard(scheme, prior, "unrestricted") == scheme


def test_apply_ramp_guard_no_prior_scheme_never_caps():
    scheme = SetScheme(sets=5, reps=5, load=500.0, rest_seconds=120)
    assert apply_ramp_guard(scheme, None, "beginner") == scheme


def test_apply_ramp_guard_caps_load_increase_for_beginner():
    prior = SetScheme(sets=3, reps=5, load=100.0, rest_seconds=120)
    scheme = SetScheme(sets=3, reps=5, load=150.0, rest_seconds=120)  # +50%, way over the +20% cap

    capped = apply_ramp_guard(scheme, prior, "beginner")

    assert capped.load == 120.0
    assert capped.note == "ramp_capped"


def test_apply_ramp_guard_does_not_cap_increase_within_bounds():
    prior = SetScheme(sets=3, reps=5, load=100.0, rest_seconds=120)
    scheme = SetScheme(sets=3, reps=5, load=105.0, rest_seconds=120)  # +5%, under the +20% cap

    assert apply_ramp_guard(scheme, prior, "beginner") == scheme


def test_apply_ramp_guard_post_amber_uses_the_tighter_load_cap():
    prior = SetScheme(sets=3, reps=5, load=100.0, rest_seconds=120)
    scheme = SetScheme(sets=3, reps=5, load=110.0, rest_seconds=120)  # +10%, over the +2.5% post-amber cap

    capped = apply_ramp_guard(scheme, prior, "post_amber")

    assert capped.load == 102.5


def test_apply_ramp_guard_caps_set_count_increase():
    prior = SetScheme(sets=3, reps=5, load=None, rest_seconds=120)
    scheme = SetScheme(sets=6, reps=5, load=None, rest_seconds=120)  # +100%, way over the +20% cap

    capped = apply_ramp_guard(scheme, prior, "beginner")

    assert capped.sets == 3  # int(3 * 1.20) truncates to 3 - no increase allowed yet


def test_apply_ramp_guard_preserves_deload_note_instead_of_overwriting():
    prior = SetScheme(sets=3, reps=5, load=100.0, rest_seconds=120)
    scheme = SetScheme(sets=3, reps=5, load=150.0, rest_seconds=120, note="deload")

    capped = apply_ramp_guard(scheme, prior, "beginner")

    assert capped.note == "deload"


def test_apply_ramp_guard_handles_missing_load_gracefully():
    prior = SetScheme(sets=3, reps=5, load=None, rest_seconds=120)
    scheme = SetScheme(sets=3, reps=5, load=None, rest_seconds=120)

    assert apply_ramp_guard(scheme, prior, "beginner") == scheme
