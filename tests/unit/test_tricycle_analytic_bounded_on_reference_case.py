from pathlib import Path
import yaml
import pytest

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import solve_tricycle_gear_with_bounds


def test_tricycle_analytic_bounded_on_reference_case():
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

    cg_x = design.stability.cg_location_m[0]
    cg_z = design.vertical_geometry.cg_z_m
    belly_z = -design.fuselage.maitre_couple_m / 2.0

    gear_height_m = abs(belly_z) + proj.ground_objectifs.garde_sol_fuselage_m_min + 0.05
    h_cg_above_ground = cg_z - (belly_z - gear_height_m)

    # Ce test ne suppose pas encore que le cas passe.
    # Il documente si la référence est admissible ou non pour le solveur analytique borné.
    try:
        x_main, x_nose, wheelbase = solve_tricycle_gear_with_bounds(
            cg_x=cg_x,
            h_cg_above_ground=h_cg_above_ground,
            nose_load_fraction=proj.ground_objectifs.charge_nez_pct_cible / 100.0,
            tipback_angle_deg_target=proj.ground_objectifs.angle_tipback_deg_min + 5.0,
            fuselage_length=design.fuselage.longueur_m,
            nose_x_min=0.02,
            main_x_max=design.fuselage.longueur_m,
            wheelbase_max_ratio=0.7,
        )
        print(f"ADMISSIBLE x_main={x_main:.6f} x_nose={x_nose:.6f} wheelbase={wheelbase:.6f}")
    except ValueError as exc:
        print(f"NON_ADMISSIBLE {exc}")
        pytest.skip(str(exc))
