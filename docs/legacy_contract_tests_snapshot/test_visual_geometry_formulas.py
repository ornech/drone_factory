from pathlib import Path
import sys
import yaml
import pytest
import math

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_visual_geometry_snapshot():
    # Load the reference example
    yaml_path = ROOT / "examples" / "uav_obs_01_ref" / "project.yaml"
    data = load_yaml(yaml_path)
    
    # Parse with Pydantic
    project_input = ProjectInput.model_validate(data)
    
    # Run full pipeline (does not modify src/, uses current formulas)
    orchestrator = PipelineOrchestrator(project_input, yaml_path.parent)
    success = orchestrator.run()
    assert success == True, "Pipeline must succeed on reference without blocking issues"
    
    design = orchestrator.design
    
    # Verify key input fields to visual formulas are frozen (min cover required)
    assert design.wing_geometry.envergure_m == pytest.approx(2.20, abs=0.01)
    assert design.wing_geometry.surface_alaire_m2 == pytest.approx(0.60, abs=0.01)
    assert design.wing_geometry.mac_m == pytest.approx(0.283, abs=0.01)
    assert design.wing_geometry.corde_racine_m == pytest.approx(0.364, abs=0.01)
    assert design.empennages.surface_h_m2 == pytest.approx(0.160, abs=0.01)
    assert design.vertical_geometry.wheel_radius_m == pytest.approx(0.070, abs=0.001)
    
    # Compute current visual geometry values per FORMULAS.md and ac3d_writer.py logic
    wg = design.wing_geometry
    emp = design.empennages
    gr = design.ground_reactions
    
    visual_values = {
        "fuselage_length_m": wg.envergure_m * 0.7,
        "fuselage_width_m": wg.corde_racine_m * 0.8,
        "fuselage_height_m": wg.corde_racine_m * 1.0,
        "wing_root_le_x_m": wg.mac_m * 0.5,
        "htail_span_m": math.sqrt(emp.surface_h_m2 * 3.0),
        "htail_chord_root_m": emp.surface_h_m2 / math.sqrt(emp.surface_h_m2 * 3.0),
        "htail_chord_tip_m": (emp.surface_h_m2 / math.sqrt(emp.surface_h_m2 * 3.0)) * 0.8,
        "wheel_width_m": gr.wheel_radius_m * 0.5,
    }
    
    # Snapshot expected values from current formulas (fails if formulas change)
    expected = {
        "fuselage_length_m": pytest.approx(1.54, abs=0.01),
        "fuselage_width_m": pytest.approx(0.291, abs=0.01),
        "fuselage_height_m": pytest.approx(0.364, abs=0.01),
        "wing_root_le_x_m": pytest.approx(0.141, abs=0.01),
        "htail_span_m": pytest.approx(0.693, abs=0.01),
        "htail_chord_root_m": pytest.approx(0.231, abs=0.01),
        "htail_chord_tip_m": pytest.approx(0.185, abs=0.01),
        "wheel_width_m": pytest.approx(0.035, abs=0.001),
    }
    
    assert visual_values == expected, "Visual geometry formulas have changed"
