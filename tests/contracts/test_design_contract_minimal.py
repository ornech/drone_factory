from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import calculate_ground_systems


def test_design_contract_minimal():
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

    # CONTRATS MINIMAUX (FlightGear tolère mal les incohérences)

    assert design.wing_geometry.surface_alaire_m2 > 0.1
    assert design.wing_geometry.envergure_m > 0.5

    assert design.vertical_geometry.cg_z_m > 0.0

    assert design.power_and_battery.puissance_requise_croisiere_w > 10

    gr = design.ground_reactions
    assert gr.empattement_m > 0.05

    # Contrat critique : CG au-dessus du sol
    vg = design.vertical_geometry
    h = vg.cg_z_m - (vg.fuselage_bottom_z_m - vg.gear_z_m)

    assert h > 0.0
