from pathlib import Path
import json
import yaml
import pytest

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import calculate_ground_systems


def test_ground_reactions_match_reference():
    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    ref_json = spec / "references" / "uav_obs_01" / "Reports" / "derived_design.json"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    ref = json.loads(ref_json.read_text(encoding="utf-8"))

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

    assert gr.empattement_m == pytest.approx(
        ref["ground_reactions"]["empattement_m"], abs=0.005
    )
    assert gr.charge_nez_pct_calculee == pytest.approx(
        ref["ground_reactions"]["charge_nez_pct_calculee"], abs=0.5
    )

    for i in range(3):
        assert gr.nose_gear_pos[i] == pytest.approx(
            ref["ground_reactions"]["nose_gear_pos"][i], abs=0.005
        )
        assert gr.main_gear_left_pos[i] == pytest.approx(
            ref["ground_reactions"]["main_gear_left_pos"][i], abs=0.005
        )
        assert gr.main_gear_right_pos[i] == pytest.approx(
            ref["ground_reactions"]["main_gear_right_pos"][i], abs=0.005
        )
