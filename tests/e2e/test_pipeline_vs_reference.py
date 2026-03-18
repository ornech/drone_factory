import json
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


def test_pipeline_matches_reference(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"
    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    project_input = ProjectInput(**data)

    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run(), "Pipeline a échoué"

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
        assert gen_file.exists(), f"Manquant: {gen_file}"

    ET.parse(generated / "JSBSim" / "uav_obs_01.xml")
    ET.parse(generated / "uav_obs_01-set.xml")
    ET.parse(generated / "Models" / "uav_obs_01-model.xml")

    set_root = ET.parse(generated / "uav_obs_01-set.xml").getroot()
    model_root = ET.parse(generated / "Models" / "uav_obs_01-model.xml").getroot()
    jsb_text = (generated / "JSBSim" / "uav_obs_01.xml").read_text(encoding="utf-8")
    ac_text = (generated / "Models" / "uav_obs_01.ac").read_text(encoding="utf-8")

    flight_model = set_root.find("./sim/flight-model")
    aero = set_root.find("./sim/aero")
    path_node = model_root.find("./path")

    assert flight_model is not None
    assert aero is not None
    assert path_node is not None

    assert flight_model.text == "jsb"
    assert aero.text == "JSBSim/uav_obs_01"
    assert path_node.text == "uav_obs_01.ac"

    assert "<ground_reactions>" in jsb_text
    assert "<propulsion>" in jsb_text
    assert "AC3Db" in ac_text

    gen = json.loads((generated / "Reports" / "derived_design.json").read_text(encoding="utf-8"))

    mass = gen["mass_budget"]
    wing = gen["wing_geometry"]
    ground = gen["ground_reactions"]
    vertical = gen["vertical_geometry"]

    assert mass["mtow_kg"] > 0
    assert mass["masse_vide_kg"] > 0
    assert mass["masse_batterie_kg"] > 0
    assert mass["masse_charge_utile_kg"] >= 0

    assert wing["surface_alaire_m2"] > 0
    assert wing["envergure_m"] > 0
    assert wing["mac_m"] > 0

    assert ground["empattement_m"] > 0
    assert ground["voie_m"] > 0
    assert 0 < ground["charge_nez_pct_calculee"] < 100

    nose_x = ground["nose_gear_pos"][0]
    main_left_x = ground["main_gear_left_pos"][0]
    main_right_x = ground["main_gear_right_pos"][0]
    cg_x = gen["stability"]["cg_location_m"][0]

    assert nose_x < cg_x < main_left_x
    assert main_left_x == main_right_x

    assert ground["main_gear_left_pos"][1] < 0
    assert ground["main_gear_right_pos"][1] > 0

    assert vertical["cg_z_m"] > 0
    assert vertical["fuselage_bottom_z_m"] >= 0
    assert vertical["prop_tip_z_m"] >= 0
