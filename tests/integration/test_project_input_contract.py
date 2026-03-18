from pathlib import Path
import yaml
from uav_generator.data_models import ProjectInput

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "external" / "drone_spec"

def test_project_input_accepts_spec_fixture():
    data = yaml.safe_load((SPEC / "fixtures" / "uav_obs_01_ref" / "project.yaml").read_text(encoding="utf-8"))
    obj = ProjectInput(**data)
    assert obj.projet.nom == "uav_obs_01"
