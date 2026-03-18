from pathlib import Path
import yaml
import pytest

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import (
    calculate_ground_systems,
    solve_tricycle_gear_analytically,
)


def test_tricycle_analytic_vs_current_solver_on_reference_case():
    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    proj = ProjectInput(**data)
    design = DerivedDesign()

    design = calculate_mass_budget(proj, design)
    design = calculate_control_system(proj, design)
    design = calculate_aero(proj, design)
    design = calculate_vertical_geometry(proj, design)
    design = calculate_propulsion(proj, design)
    design = calculate_ground_systems(proj, design)

    gr = design.ground_reactions
    vg = design.vertical_geometry
    assert gr is not None
    assert vg is not None

    cg_x = design.stability.cg_location_m[0]
    h_cg_above_ground = vg.cg_z_m - (vg.fuselage_bottom_z_m - vg.gear_z_m)

    x_main_a, x_nose_a, wb_a = solve_tricycle_gear_analytically(
        cg_x=cg_x,
        h_cg_above_ground=h_cg_above_ground,
        nose_load_fraction=proj.ground_objectifs.charge_nez_pct_cible / 100.0,
        tipback_angle_deg_target=proj.ground_objectifs.angle_tipback_deg_min + 5.0,
    )

    # Le solver courant n'a pas à reproduire exactement la solution analytique non bornée.
    # Il doit rester du même ordre de grandeur sur la distance CG -> train principal.
    d_current = gr.main_gear_left_pos[0] - cg_x
    d_analytic = x_main_a - cg_x

    assert d_current == pytest.approx(d_analytic, abs=0.01)
