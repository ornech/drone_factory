from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import calculate_ground_systems


def test_ground_solver_robustness_cg_variation():
    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    for delta in [-0.02, -0.01, 0.0, 0.01, 0.02]:
        proj = ProjectInput(**data)
        design = DerivedDesign()

        design = calculate_mass_budget(proj, design)
        design = calculate_control_system(proj, design)
        design = calculate_aero(proj, design)

        # Perturbation CG
        design.stability.cg_cible_pct_mac += delta

        design = calculate_vertical_geometry(proj, design)
        design = calculate_propulsion(proj, design)
        design = calculate_ground_systems(proj, design)

        gr = design.ground_reactions

        assert gr is not None
        assert gr.empattement_m > 0.05
