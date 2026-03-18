from pathlib import Path
import yaml
import pytest

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "external" / "drone_spec"

def test_visual_geometry_runtime_values_are_stable(tmp_path):
    yaml_path = SPEC / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    project_input = ProjectInput.model_validate(data)

    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run() is True

    vg = orchestrator.design.visual_geometry
    assert vg is not None

    assert vg.fuselage_length_m == pytest.approx(1.54, abs=0.01)
    assert vg.fuselage_width_m == pytest.approx(0.291, abs=0.01)
    assert vg.fuselage_height_m == pytest.approx(0.364, abs=0.01)
    assert vg.wing_root_le_x_m == pytest.approx(0.141, abs=0.01)
    assert vg.wing_z_m == pytest.approx(0.364, abs=0.01)
    assert vg.htail_arm_x_m == pytest.approx(0.849, abs=0.01)
    assert vg.htail_span_m == pytest.approx(0.693, abs=0.01)
    assert vg.htail_chord_root_m == pytest.approx(0.231, abs=0.01)
    assert vg.htail_chord_tip_m == pytest.approx(0.185, abs=0.01)
    assert vg.htail_z_m == pytest.approx(0.291, abs=0.01)
    assert vg.wheel_width_m == pytest.approx(0.035, abs=0.001)
