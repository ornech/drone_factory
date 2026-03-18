from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "external" / "drone_spec"

def test_reference_pipeline_runs_against_spec_fixture(tmp_path):
    yaml_path = SPEC / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    project_input = ProjectInput.model_validate(data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    result = orchestrator.run()
    assert result is True
