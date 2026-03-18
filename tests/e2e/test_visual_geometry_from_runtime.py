from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


SPEC = Path(__file__).resolve().parents[2] / "external" / "drone_spec"


def test_visual_geometry_runtime_values_are_stable(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    yaml_path = SPEC / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    project_input = ProjectInput.model_validate(data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run() is True

    vg = orchestrator.design.visual_geometry
    assert vg is not None

    assert vg.fuselage_length_m > 0
    assert vg.fuselage_width_m > 0
    assert vg.fuselage_height_m > 0
    assert vg.wing_root_le_x_m >= 0
    assert vg.wing_z_m > 0
    assert vg.htail_arm_x_m > 0
    assert vg.htail_span_m > 0
    assert vg.htail_chord_root_m > 0
    assert vg.htail_chord_tip_m > 0
    assert vg.htail_z_m >= 0
    assert vg.wheel_width_m > 0
