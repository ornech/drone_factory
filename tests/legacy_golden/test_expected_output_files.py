from pathlib import Path


def test_expected_reference_output_files_exist():
    root = Path(__file__).resolve().parents[2]
    output = root / "external" / "drone_spec" / "fixtures" / "uav_obs_01_ref" / "output" / "uav_obs_01"
    expected = [
        output / "JSBSim" / "uav_obs_01.xml",
        output / "uav_obs_01-set.xml",
        output / "Models" / "uav_obs_01.ac",
        output / "Models" / "uav_obs_01-model.xml",
        output / "Systems" / "flight-control.xml",
        output / "Reports" / "derived_design.json",
    ]
    missing = [str(p) for p in expected if not p.exists()]
    assert not missing, "Fichiers manquants:\n" + "\n".join(missing)
