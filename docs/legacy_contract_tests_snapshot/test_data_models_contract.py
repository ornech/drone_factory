from pathlib import Path
import sys
import yaml
import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from uav_generator.data_models import ProjectInput, DerivedDesign

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_project_input_accepts_reference_yaml():
    data = load_yaml(ROOT / "examples" / "uav_obs_01_ref" / "project.yaml")
    obj = ProjectInput(**data)
    assert obj.projet.nom == "uav_obs_01"

def test_project_input_rejects_unknown_root_key():
    data = load_yaml(ROOT / "examples" / "uav_obs_01_ref" / "project.yaml")
    data["truc_non_prevu"] = 1
    with pytest.raises(ValidationError):
        ProjectInput(**data)

def test_project_input_rejects_unknown_nested_key_in_projet():
    data = load_yaml(ROOT / "examples" / "uav_obs_01_ref" / "project.yaml")
    data["projet"]["cle_inconnue"] = "x"
    with pytest.raises(ValidationError):
        ProjectInput(**data)

def test_derived_design_currently_allows_extra_fields():
    obj = DerivedDesign(truc_libre=123)
    assert getattr(obj, "truc_libre", None) == 123

def test_derived_design_known_fields_inventory():
    expected = {
        "mass_budget",
        "wing_geometry",
        "stability",
        "empennages",
        "gouvernes",
        "fuselage",
        "power_and_battery",
        "ground_reactions",
        "control_system",
        "vertical_geometry",
        "blocking_issues",
    }
    actual = set(DerivedDesign.model_fields.keys())
    assert actual == expected
