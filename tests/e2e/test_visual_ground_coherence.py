from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


SPEC = Path(__file__).resolve().parents[2] / "external" / "drone_spec"


def test_visual_ground_coherence(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    yaml_path = SPEC / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    project_input = ProjectInput.model_validate(data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run() is True

    vg = orchestrator.design.visual_geometry
    gr = orchestrator.design.ground_reactions
    phys = orchestrator.design.vertical_geometry

    assert vg is not None
    assert gr is not None
    assert phys is not None

    # Largeur de roue visuelle cohérente
    assert vg.wheel_width_m > 0

    # Le train principal doit rester sous le volume général, pas derrière le monde.
    assert 0 <= gr.main_gear_left_pos[0] <= 2.5
    assert 0 <= gr.main_gear_right_pos[0] <= 2.5
    assert 0 <= gr.nose_gear_pos[0] <= 2.5

    # Le fuselage visuel doit être plus long que l'empattement.
    assert vg.fuselage_length_m > gr.empattement_m

    # La hauteur visuelle du fuselage doit être cohérente avec la garde au sol physique.
    assert vg.fuselage_height_m > 0
    assert phys.fuselage_bottom_z_m > 0
