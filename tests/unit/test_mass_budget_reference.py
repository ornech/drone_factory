from pathlib import Path
import json
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget


def test_mass_budget_matches_reference():
    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    ref_json = spec / "references" / "uav_obs_01" / "Reports" / "derived_design.json"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    ref = json.loads(ref_json.read_text(encoding="utf-8"))

    proj = ProjectInput(**data)
    design = DerivedDesign()
    design = calculate_mass_budget(proj, design)

    mb = design.mass_budget
    assert mb is not None

    assert mb.mtow_kg == ref["mass_budget"]["mtow_kg"]
    assert mb.masse_vide_kg == ref["mass_budget"]["masse_vide_kg"]
    assert mb.masse_batterie_kg == ref["mass_budget"]["masse_batterie_kg"]
    assert mb.masse_charge_utile_kg == ref["mass_budget"]["masse_charge_utile_kg"]
