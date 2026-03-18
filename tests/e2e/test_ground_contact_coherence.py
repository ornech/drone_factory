from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


SPEC = Path(__file__).resolve().parents[2] / "external" / "drone_spec"


def test_ground_contact_coherence(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    yaml_path = SPEC / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    project_input = ProjectInput.model_validate(data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run() is True

    gr = orchestrator.design.ground_reactions
    vg = orchestrator.design.vertical_geometry
    assert gr is not None
    assert vg is not None

    wheel_r = vg.wheel_radius_m

    nose_z = gr.nose_gear_pos[2]
    left_z = gr.main_gear_left_pos[2]
    right_z = gr.main_gear_right_pos[2]

    # Les trois roues doivent toucher le même plan de sol.
    assert nose_z == left_z == right_z

    # Le bas des roues doit être au sol : centre roue = -rayon.
    assert nose_z == -wheel_r
    assert left_z == -wheel_r
    assert right_z == -wheel_r

    # Le CG doit être au-dessus du train.
    assert vg.cg_z_m > vg.gear_z_m

    # Le fuselage ne doit pas couper le sol.
    assert vg.fuselage_bottom_z_m > 0

    # L'hélice ne doit pas couper le sol.
    assert vg.prop_tip_z_m > 0

    # Les deux roues principales doivent être symétriques.
    assert gr.main_gear_left_pos[0] == gr.main_gear_right_pos[0]
    assert gr.main_gear_left_pos[1] == -gr.main_gear_right_pos[1]
    assert gr.main_gear_left_pos[2] == gr.main_gear_right_pos[2]
