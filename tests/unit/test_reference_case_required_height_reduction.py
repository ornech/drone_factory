from pathlib import Path
import math
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion


def test_reference_case_required_height_reduction():
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

    mac_m = design.wing_geometry.mac_m
    wing_le_root_x = mac_m * 0.5
    cg_x = wing_le_root_x + (
        design.stability.cg_cible_pct_mac * design.wing_geometry.mac_m
    )

    cg_z = design.vertical_geometry.cg_z_m
    belly_z = -design.fuselage.maitre_couple_m / 2.0
    fuselage_length = design.fuselage.longueur_m

    gear_height_m = abs(belly_z) + proj.ground_objectifs.garde_sol_fuselage_m_min + 0.05
    h_current = cg_z - (fuselage_bottom_z - gear_z)

    fn = proj.ground_objectifs.charge_nez_pct_cible / 100.0
    theta_deg = proj.ground_objectifs.angle_tipback_deg_min + 5.0
    theta = math.radians(theta_deg)

    nose_x_min = 0.02
    wheelbase_max_ratio = 0.7
    wheelbase_max = wheelbase_max_ratio * fuselage_length
    main_x_max = fuselage_length

    d_max_nose = (cg_x - nose_x_min) / (1.0 / fn - 1.0)
    d_max_wb = fn * wheelbase_max
    d_max_main = main_x_max - cg_x

    d_max = min(d_max_nose, d_max_wb, d_max_main)
    h_max = d_max * math.tan(theta)
    delta_h = h_current - h_max

    print(f"cg_x={cg_x:.6f}")
    print(f"fn={fn:.6f}")
    print(f"theta_deg={theta_deg:.6f}")
    print(f"fuselage_length={fuselage_length:.6f}")
    print(f"h_current={h_current:.6f}")
    print(f"d_max_nose={d_max_nose:.6f}")
    print(f"d_max_wb={d_max_wb:.6f}")
    print(f"d_max_main={d_max_main:.6f}")
    print(f"d_max={d_max:.6f}")
    print(f"h_max={h_max:.6f}")
    print(f"delta_h={delta_h:.6f}")

    assert h_max > 0.0
    assert delta_h > 0.0
