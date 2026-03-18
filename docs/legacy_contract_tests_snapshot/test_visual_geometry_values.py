from pathlib import Path
import sys
import yaml
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_visual_geometry_values_from_pipeline():
    yaml_path = ROOT / "examples" / "uav_obs_01_ref" / "project.yaml"
    data = load_yaml(yaml_path)

    project_input = ProjectInput.model_validate(data)

    orchestrator = PipelineOrchestrator(project_input, yaml_path.parent)
    assert orchestrator.run() is True

    design = orchestrator.design
    vg = design.visual_geometry

    # --- assertions DIRECTES (pas de recalcul local) ---
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
