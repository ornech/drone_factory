from pathlib import Path
import json
import yaml
from jsonschema import validate, ValidationError
import pytest

ROOT = Path(__file__).resolve().parents[2]

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def test_reference_project_matches_schema():
    schema = load_json(ROOT / "schemas" / "project.schema.json")
    data = load_yaml(ROOT / "examples" / "uav_obs_01_ref" / "project.yaml")
    validate(instance=data, schema=schema)

def test_unknown_root_field_is_rejected():
    schema = load_json(ROOT / "schemas" / "project.schema.json")
    data = load_yaml(ROOT / "examples" / "uav_obs_01_ref" / "project.yaml")
    data["champ_ajoute_par_agent"] = 123
    with pytest.raises(ValidationError):
        validate(instance=data, schema=schema)
