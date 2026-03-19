import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


@pytest.mark.skipif(shutil.which("JSBSim") is None, reason="JSBSim non installé")
def test_jsbsim_runtime_no_nan(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    repo_root = Path(__file__).resolve().parents[2]
    yaml_path = repo_root / "external" / "drone_spec" / "fixtures" / "uav_obs_01_ref" / "project.yaml"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    project_input = ProjectInput(**data)

    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run()

    root = (tmp_path / "output" / "uav_obs_01").resolve()
    assert root.exists(), f"Export manquant: {root}"

    jsbsim_root = tmp_path / "jsbsim_root"
    (jsbsim_root / "aircraft").mkdir(parents=True)

    link_dir = jsbsim_root / "aircraft" / "uav_obs_01"
    link_dir.symlink_to(root, target_is_directory=True)

    xml_link = link_dir / "uav_obs_01.xml"
    xml_target = root / "JSBSim" / "uav_obs_01.xml"
    assert xml_target.exists(), f"XML cible manquant: {xml_target}"
    if not xml_link.exists():
        xml_link.symlink_to(xml_target)

    init = tmp_path / "init.xml"
    init.write_text(
        """<?xml version="1.0"?>
<initialize name="uav_obs_01 test init">
  <latitude unit="DEG">48.0</latitude>
  <longitude unit="DEG">-1.0</longitude>
  <altitude unit="FT">300</altitude>
  <phi unit="DEG">0</phi>
  <theta unit="DEG">0</theta>
  <psi unit="DEG">0</psi>
  <ubody unit="FT/SEC">0</ubody>
  <vbody unit="FT/SEC">0</vbody>
  <wbody unit="FT/SEC">0</wbody>
</initialize>
""",
        encoding="utf-8",
    )

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
