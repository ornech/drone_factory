from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


def test_ac3d_ground_objects_exist_when_ground_exists(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    project_input = ProjectInput(**data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run()

    gr = orchestrator.design.ground_reactions
    assert gr is not None

    ac_path = tmp_path / "output" / "uav_obs_01" / "Models" / "uav_obs_01.ac"
    txt = ac_path.read_text(encoding="utf-8")

    # si le solver physique produit trois roues, le modèle visuel doit aussi les contenir
    assert gr.nose_gear_pos is not None
    assert gr.main_gear_left_pos is not None
    assert gr.main_gear_right_pos is not None

    assert 'name "nose_wheel"' in txt
    assert 'name "left_wheel"' in txt
    assert 'name "right_wheel"' in txt
