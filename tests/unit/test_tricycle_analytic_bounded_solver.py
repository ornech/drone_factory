import pytest

from uav_generator.calculators.ground import solve_tricycle_gear_with_bounds


def test_tricycle_analytic_bounded_solver_accepts_plausible_case():
    x_main, x_nose, wheelbase = solve_tricycle_gear_with_bounds(
        cg_x=0.35,
        h_cg_above_ground=0.08,
        nose_load_fraction=0.20,
        tipback_angle_deg_target=70.0,
        fuselage_length=1.20,
        nose_x_min=0.02,
        main_x_max=1.20,
        wheelbase_max_ratio=0.7,
    )

    assert x_main > 0.35
    assert x_nose >= 0.02
    assert wheelbase > 0.0
    assert wheelbase <= 0.7 * 1.20


def test_tricycle_analytic_bounded_solver_rejects_nose_out_of_bounds():
    with pytest.raises(ValueError, match="nose gear position"):
        solve_tricycle_gear_with_bounds(
            cg_x=0.20,
            h_cg_above_ground=0.10,
            nose_load_fraction=0.20,
            tipback_angle_deg_target=20.0,
            fuselage_length=1.20,
            nose_x_min=0.02,
            main_x_max=1.20,
            wheelbase_max_ratio=0.7,
        )


def test_tricycle_analytic_bounded_solver_rejects_wheelbase_out_of_bounds():
    with pytest.raises(ValueError, match="wheelbase"):
        solve_tricycle_gear_with_bounds(
            cg_x=0.50,
            h_cg_above_ground=0.10,
            nose_load_fraction=0.30,
            tipback_angle_deg_target=60.0,
            fuselage_length=0.40,
            nose_x_min=0.02,
            main_x_max=0.80,
            wheelbase_max_ratio=0.3,
        )
