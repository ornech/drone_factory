from pathlib import Path
import yaml
import math

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


def parse_ac3d_object_locations(ac_text: str) -> dict:
    locations = {}
    current_name = None

    for line in ac_text.splitlines():
        line = line.strip()
        if line.startswith('name "'):
            current_name = line[len('name "'):-1]
        elif line.startswith("loc ") and current_name is not None:
            _, x, y, z = line.split()
            locations[current_name] = (float(x), float(y), float(z))
            current_name = None

    return locations


def test_ac3d_object_locations_match_design(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    project_input = ProjectInput(**data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run()

    design = orchestrator.design
    assert design.ground_reactions is not None
    assert design.visual_geometry is not None

    ac_path = tmp_path / "output" / "uav_obs_01" / "Models" / "uav_obs_01.ac"
    ac_text = ac_path.read_text(encoding="utf-8")
    locs = parse_ac3d_object_locations(ac_text)

    def design_to_ac3d(pos):
        return (-pos[0], pos[1], pos[2])

    gr = design.ground_reactions
    vg = design.visual_geometry

    wheel_radius = gr.wheel_radius_m

    expected_nose = design_to_ac3d((gr.nose_gear_pos[0], gr.nose_gear_pos[1], gr.nose_gear_pos[2] + wheel_radius))
    expected_left = design_to_ac3d((gr.main_gear_left_pos[0], gr.main_gear_left_pos[1], gr.main_gear_left_pos[2] + wheel_radius))
    expected_right = design_to_ac3d((gr.main_gear_right_pos[0], gr.main_gear_right_pos[1], gr.main_gear_right_pos[2] + wheel_radius))

    assert locs["nose_wheel"] == expected_nose
    assert locs["left_wheel"] == expected_left
    assert locs["right_wheel"] == expected_right

    expected_wing = design_to_ac3d((vg.wing_root_le_x_m, 0, vg.wing_z_m))
    expected_htail = design_to_ac3d((vg.htail_arm_x_m, 0, vg.htail_z_m))

    assert locs["main_wing"] == expected_wing
    assert locs["h_stab"] == expected_htail
