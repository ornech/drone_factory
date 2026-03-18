from pathlib import Path
import math
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import calculate_ground_systems


def test_ground_tipback_report_consistency():
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
    h = vg.cg_z_m - (vg.fuselage_bottom_z_m - vg.gear_z_m)
    d = gr.main_gear_left_pos[0] - cg_x

    rebuilt_tipback = math.degrees(math.atan(h / d))

    print(f"stored_tipback={gr.angle_tipback_deg_calcule:.6f}")
    print(f"rebuilt_tipback={rebuilt_tipback:.6f}")

    assert gr.angle_tipback_deg_calcule == rebuilt_tipback
