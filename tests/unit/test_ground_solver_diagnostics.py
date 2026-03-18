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


def test_ground_solver_diagnostics():
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
    vg = design.vertical_geometry
    cg_z = vg.cg_z_m
    gear_z = vg.gear_z_m
    fuselage_bottom_z = vg.fuselage_bottom_z_m
    h_cg_above_ground = cg_z - (fuselage_bottom_z - gear_z)

    d_current = gr.main_gear_left_pos[0] - cg_x
    tipback_current = math.degrees(math.atan(h_cg_above_ground / d_current))
    nose_fraction_current = (gr.main_gear_left_pos[0] - cg_x) / gr.empattement_m

    print(f"cg_x={cg_x:.6f}")
    print(f"h_cg_above_ground={h_cg_above_ground:.6f}")
    print(f"d_current={d_current:.6f}")
    print(f"wheelbase={gr.empattement_m:.6f}")
    print(f"tipback_current={tipback_current:.6f}")
    print(f"nose_fraction_current={nose_fraction_current:.6f}")

    assert d_current > 0
    assert gr.empattement_m > 0
