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
    assert gr is not None

    cg_x = design.stability.cg_location_m[0]
    cg_z = design.vertical_geometry.cg_z_m
    belly_z = -design.fuselage.maitre_couple_m / 2.0

    gear_height_m = abs(belly_z) + proj.ground_objectifs.garde_sol_fuselage_m_min + 0.05
    h_cg_above_ground = cg_z - (belly_z - gear_height_m)

    x_main_a, x_nose_a, wb_a = solve_tricycle_gear_analytically(
        cg_x=cg_x,
        h_cg_above_ground=h_cg_above_ground,
        nose_load_fraction=proj.ground_objectifs.charge_nez_pct_cible / 100.0,
        tipback_angle_deg_target=proj.ground_objectifs.angle_tipback_deg_min + 5.0,
    )

    # On ne demande pas encore l'égalité.
    # On veut mesurer si le solver actuel est "proche" d'une solution analytique.
    assert gr.empattement_m == pytest.approx(wb_a, abs=0.03)
    assert gr.nose_gear_pos[0] == pytest.approx(x_nose_a, abs=0.03)
    assert gr.main_gear_left_pos[0] == pytest.approx(x_main_a, abs=0.03)
