from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "external" / "drone_spec"

def test_spec_reference_inventory_is_present():
    ref = SPEC / "references" / "uav_obs_01"
    expected = [
        ref / "JSBSim" / "uav_obs_01.xml",
        ref / "uav_obs_01-set.xml",
        ref / "Models" / "uav_obs_01.ac",
        ref / "Models" / "uav_obs_01-model.xml",
        ref / "Systems" / "flight-control.xml",
        ref / "Reports" / "derived_design.json",
    ]
    missing = [str(p) for p in expected if not p.exists()]
    assert not missing, "Inventaire spec incomplet:\n" + "\n".join(missing)
