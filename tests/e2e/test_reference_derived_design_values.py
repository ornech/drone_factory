from pathlib import Path
import json
import yaml
import pytest

from uav_generator.pipeline import PipelineOrchestrator
from uav_generator.data_models import ProjectInput


def test_reference_derived_design_values(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    ref_json = spec / "references" / "uav_obs_01" / "Reports" / "derived_design.json"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    ref = json.loads(ref_json.read_text(encoding="utf-8"))

    project_input = ProjectInput(**data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run()

    gen_json = tmp_path / "output" / "uav_obs_01" / "Reports" / "derived_design.json"
    gen = json.loads(gen_json.read_text(encoding="utf-8"))

    assert gen["mass_budget"]["mtow_kg"] == ref["mass_budget"]["mtow_kg"]
    assert gen["mass_budget"]["masse_vide_kg"] == ref["mass_budget"]["masse_vide_kg"]
    assert gen["mass_budget"]["masse_batterie_kg"] == ref["mass_budget"]["masse_batterie_kg"]

    assert gen["wing_geometry"]["surface_alaire_m2"] == ref["wing_geometry"]["surface_alaire_m2"]
    assert gen["wing_geometry"]["envergure_m"] == ref["wing_geometry"]["envergure_m"]

    # Solver sol heuristique : comparaison avec tolérance, pas égalité binaire
    assert gen["ground_reactions"]["empattement_m"] == pytest.approx(
        ref["ground_reactions"]["empattement_m"], abs=0.005
    )
    assert gen["ground_reactions"]["charge_nez_pct_calculee"] == pytest.approx(
        ref["ground_reactions"]["charge_nez_pct_calculee"], abs=0.5
    )

    for i in range(3):
        assert gen["ground_reactions"]["nose_gear_pos"][i] == pytest.approx(
            ref["ground_reactions"]["nose_gear_pos"][i], abs=0.005
        )
        assert gen["ground_reactions"]["main_gear_left_pos"][i] == pytest.approx(
            ref["ground_reactions"]["main_gear_left_pos"][i], abs=0.005
        )
        assert gen["ground_reactions"]["main_gear_right_pos"][i] == pytest.approx(
            ref["ground_reactions"]["main_gear_right_pos"][i], abs=0.005
        )
