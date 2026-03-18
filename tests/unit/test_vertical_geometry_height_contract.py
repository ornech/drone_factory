from pathlib import Path
import math
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion


def test_vertical_geometry_height_contract():
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

    vg = design.vertical_geometry
    fuselage_length = design.fuselage.longueur_m

    cg_z = vg.cg_z_m
    gear_z = vg.gear_z_m
    fuselage_bottom_z = vg.fuselage_bottom_z_m

    # Nouveau contrat vertical : hauteur du CG au-dessus du sol reconstruite
    # à partir des sorties du vertical solver lui-même.
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

    print(f"h_current={h_current:.6f}")
    print(f"h_max={h_max:.6f}")

    assert h_current <= h_max, (
        f"vertical_geometry produit un CG trop haut pour un train analytique réaliste: "
        f"h_current={h_current:.6f} > h_max={h_max:.6f}"
    )
