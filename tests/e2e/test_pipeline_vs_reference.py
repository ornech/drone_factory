from pathlib import Path
import json
import yaml
import pytest

from uav_generator.pipeline import PipelineOrchestrator
from uav_generator.data_models import ProjectInput


def test_pipeline_matches_reference(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    reference = spec / "references" / "uav_obs_01"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    project_input = ProjectInput(**data)

    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    success = orchestrator.run()
    assert success, "Pipeline a échoué"

    generated = tmp_path / "output" / "uav_obs_01"

    expected_files = [
        "JSBSim/uav_obs_01.xml",
        "uav_obs_01-set.xml",
        "Models/uav_obs_01.ac",
        "Models/uav_obs_01-model.xml",
        "Systems/flight-control.xml",
        "Reports/derived_design.json",
    ]

    for rel in expected_files:
        gen_file = generated / rel
        ref_file = reference / rel
        assert gen_file.exists(), f"Manquant: {gen_file}"
        assert ref_file.exists(), f"Reference manquante: {ref_file}"

    gen = json.loads((generated / "Reports" / "derived_design.json").read_text(encoding="utf-8"))
    ref = json.loads((reference / "Reports" / "derived_design.json").read_text(encoding="utf-8"))

    assert gen["mass_budget"]["mtow_kg"] == ref["mass_budget"]["mtow_kg"]
    assert gen["mass_budget"]["masse_vide_kg"] == ref["mass_budget"]["masse_vide_kg"]
    assert gen["mass_budget"]["masse_batterie_kg"] == ref["mass_budget"]["masse_batterie_kg"]

    assert gen["wing_geometry"]["surface_alaire_m2"] == ref["wing_geometry"]["surface_alaire_m2"]
    assert gen["wing_geometry"]["envergure_m"] == ref["wing_geometry"]["envergure_m"]

    assert gen["ground_reactions"]["empattement_m"] == pytest.approx(
        ref["ground_reactions"]["empattement_m"], abs=0.005
    )
    assert gen["ground_reactions"]["charge_nez_pct_calculee"] == pytest.approx(
        ref["ground_reactions"]["charge_nez_pct_calculee"], abs=0.5
    )
