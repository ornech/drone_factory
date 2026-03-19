import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("JSBSim") is None, reason="JSBSim non installé")
def test_jsbsim_runtime_no_nan(tmp_path):
    root = Path("runtime_export/output/uav_obs_01").resolve()

    jsbsim_root = tmp_path / "jsbsim_root"
    (jsbsim_root / "aircraft").mkdir(parents=True)

    link_dir = jsbsim_root / "aircraft" / "uav_obs_01"
    link_dir.symlink_to(root, target_is_directory=True)

    xml_link = link_dir / "uav_obs_01.xml"
    xml_target = root / "JSBSim" / "uav_obs_01.xml"
    if not xml_link.exists():
        xml_link.symlink_to(xml_target)

    init = tmp_path / "init.xml"
    init.write_text("""<?xml version="1.0"?>
<initialize>
  <latitude unit="DEG">48</latitude>
  <longitude unit="DEG">-1</longitude>
  <altitude unit="FT">300</altitude>
  <phi unit="DEG">0</phi>
  <theta unit="DEG">0</theta>
  <psi unit="DEG">0</psi>
  <ubody unit="FT/SEC">0</ubody>
  <vbody unit="FT/SEC">0</vbody>
  <wbody unit="FT/SEC">0</wbody>
</initialize>
""")

    cmd = [
        "JSBSim",
        f"--root={jsbsim_root}",
        "--aircraft=uav_obs_01",
        f"--initfile={init}",
        "--end=2",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10,
    )

    out = (result.stdout + result.stderr).lower()

    assert result.returncode == 0, out
    assert "nan" not in out
    assert "invalid" not in out
    assert "failed" not in out
