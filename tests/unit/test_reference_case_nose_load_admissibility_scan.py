from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import solve_tricycle_gear_with_bounds


def test_reference_case_nose_load_admissibility_scan():
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

    # Même formule que dans ground.py
    mac_m = design.wing_geometry.mac_m
    wing_le_root_x = mac_m * 0.5
    cg_x = wing_le_root_x + (
        design.stability.cg_cible_pct_mac * design.wing_geometry.mac_m
    )

    vg = design.vertical_geometry
    cg_z = vg.cg_z_m
    gear_z = vg.gear_z_m
    fuselage_bottom_z = vg.fuselage_bottom_z_m
    h_cg_above_ground = cg_z - (fuselage_bottom_z - gear_z)

    print(f"cg_x={cg_x:.6f}")
    print(f"h_cg_above_ground={h_cg_above_ground:.6f}")
    print(f"fuselage_length={design.fuselage.longueur_m:.6f}")

    admissible = []

    for pct in range(20, 91, 5):
        fn = pct / 100.0
        try:
            x_main, x_nose, wheelbase = solve_tricycle_gear_with_bounds(
                cg_x=cg_x,
                h_cg_above_ground=h_cg_above_ground,
                nose_load_fraction=fn,
                tipback_angle_deg_target=proj.ground_objectifs.angle_tipback_deg_min + 5.0,
                fuselage_length=design.fuselage.longueur_m,
                nose_x_min=0.02,
                main_x_max=design.fuselage.longueur_m,
                wheelbase_max_ratio=0.7,
            )
            admissible.append((pct, x_main, x_nose, wheelbase))
            print(
                f"ADMISSIBLE pct={pct} "
                f"x_main={x_main:.6f} x_nose={x_nose:.6f} wb={wheelbase:.6f}"
            )
        except ValueError as exc:
            print(f"REJECTED pct={pct} reason={exc}")

    assert admissible, "Aucune charge nez cible admissible trouvée sur le cas de référence"
