import json
from pathlib import Path

import pytest
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


def test_reference_derived_design_values(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"
    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    project_input = ProjectInput(**data)
    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run()

    gen_json = tmp_path / "output" / "uav_obs_01" / "Reports" / "derived_design.json"
    gen = json.loads(gen_json.read_text(encoding="utf-8"))

    mass = gen["mass_budget"]
    wing = gen["wing_geometry"]
    ground = gen["ground_reactions"]
    vertical = gen["vertical_geometry"]
    stability = gen["stability"]

    assert mass["mtow_kg"] == pytest.approx(
        mass["masse_vide_kg"] + mass["masse_batterie_kg"] + mass["masse_charge_utile_kg"],
        abs=0.02,
    )

    assert wing["surface_alaire_m2"] > 0
    assert wing["envergure_m"] > 0
    assert wing["mac_m"] > 0
    assert wing["envergure_m"] > wing["mac_m"]

    assert stability["marge_statique_pct"] > 0
    assert vertical["cg_z_m"] > 0
    assert vertical["fuselage_bottom_z_m"] >= 0
    assert vertical["prop_tip_z_m"] >= 0

    assert ground["empattement_m"] > 0
    assert ground["voie_m"] > 0
    assert 5.0 <= ground["charge_nez_pct_calculee"] <= 25.0

    nose_x = ground["nose_gear_pos"][0]
    main_x = ground["main_gear_left_pos"][0]
    cg_x = stability["cg_location_m"][0]

    assert nose_x < cg_x < main_x

    # Contrat e2e : la valeur calculée doit être plausible et cohérente,
    # mais on ne reconstruit pas ici depuis des champs hétérogènes.
    assert 5.0 <= ground["angle_tipback_deg_calcule"] <= 35.0
    assert ground["angle_tipback_deg_calcule"] == pytest.approx(19.746, abs=1.0)
