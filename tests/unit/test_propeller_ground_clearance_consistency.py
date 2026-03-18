from pathlib import Path
import yaml
import pytest

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import calculate_ground_systems


def test_propeller_ground_clearance_consistency():
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

    rebuilt_clearance = vg.prop_tip_z_m - (vg.fuselage_bottom_z_m - vg.gear_z_m)

    print(f"stored_clearance={gr.garde_sol_helice_m_calculee:.6f}")
    print(f"rebuilt_clearance={rebuilt_clearance:.6f}")

    assert gr.garde_sol_helice_m_calculee == pytest.approx(rebuilt_clearance, abs=1e-9)
    assert rebuilt_clearance >= 0.0
