from pathlib import Path
import copy
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


def test_ac3d_export_does_not_mutate_design(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    project_input = ProjectInput(**data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run()

    before = copy.deepcopy(orchestrator.design.model_dump())

    # Regénère uniquement la sortie AC3D/FG dans un autre dossier
    tmp2 = tmp_path / "second_export"
    tmp2.mkdir(parents=True, exist_ok=True)
    orchestrator.output_dir = tmp2
    assert orchestrator.run()

    after = orchestrator.design.model_dump()

    assert before == after
