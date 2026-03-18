import math
import pytest

from uav_generator.calculators.ground import solve_tricycle_gear_analytically


def test_tricycle_analytic_solver_respects_tipback_relation():
    cg_x = 0.20
    h = 0.10
    fn = 0.20
    tipback_target = 20.0

    x_main, x_nose, wheelbase = solve_tricycle_gear_analytically(
        cg_x=cg_x,
        h_cg_above_ground=h,
        nose_load_fraction=fn,
        tipback_angle_deg_target=tipback_target,
    )

    d = x_main - cg_x
    actual_tipback = math.degrees(math.atan(h / d))

    assert x_main > cg_x
    assert x_nose < x_main
    assert wheelbase == pytest.approx(x_main - x_nose)
    assert actual_tipback == pytest.approx(tipback_target)


def test_tricycle_analytic_solver_respects_nose_load_relation():
    cg_x = 0.20
    h = 0.10
    fn = 0.20
    tipback_target = 20.0

    x_main, x_nose, wheelbase = solve_tricycle_gear_analytically(
        cg_x=cg_x,
        h_cg_above_ground=h,
        nose_load_fraction=fn,
        tipback_angle_deg_target=tipback_target,
    )

    actual_fn = (x_main - cg_x) / (x_main - x_nose)

    assert actual_fn == pytest.approx(fn)
    assert wheelbase > 0.0


def test_tricycle_analytic_solver_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        solve_tricycle_gear_analytically(0.2, 0.1, 0.0, 20.0)

    with pytest.raises(ValueError):
        solve_tricycle_gear_analytically(0.2, -0.1, 0.2, 20.0)

    with pytest.raises(ValueError):
        solve_tricycle_gear_analytically(0.2, 0.1, 0.2, 0.0)
