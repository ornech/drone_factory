from pathlib import Path

import pytest
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


def test_ac3d_fuselage_uses_vertical_geometry(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"
    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    project_input = ProjectInput(**data)

    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run()

    report_path = tmp_path / "output" / "uav_obs_01" / "Reports" / "derived_design.json"
    ac_path = tmp_path / "output" / "uav_obs_01" / "Models" / "uav_obs_01.ac"

    import json
    gen = json.loads(report_path.read_text(encoding="utf-8"))

    expected_center_z = (
        gen["vertical_geometry"]["fuselage_bottom_z_m"]
        + gen["visual_geometry"]["fuselage_height_m"] / 2
    )

    text = ac_path.read_text(encoding="utf-8")

    assert "fuselage" in text.lower()
    assert f"{expected_center_z:.3f}" in text
