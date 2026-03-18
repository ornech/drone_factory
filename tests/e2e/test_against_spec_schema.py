from pathlib import Path
import json
import yaml
from jsonschema import validate

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "external" / "drone_spec"

def test_spec_fixture_still_matches_spec_schema():
    schema = json.loads((SPEC / "schemas" / "project.schema.json").read_text(encoding="utf-8"))
    data = yaml.safe_load((SPEC / "fixtures" / "uav_obs_01_ref" / "project.yaml").read_text(encoding="utf-8"))
    validate(instance=data, schema=schema)
