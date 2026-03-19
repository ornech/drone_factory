import re
from pathlib import Path

import yaml

from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator


def _read_mass_balance_values(xml_path: Path) -> tuple[float, float, float]:
    text = xml_path.read_text(encoding="utf-8")

    def extract(tag: str) -> float:
        m = re.search(rf"<{tag} unit=\"SLUG\*FT2\">\s*([0-9.]+)\s*</{tag}>", text)
        assert m is not None, f"Balise {tag} introuvable dans {xml_path}"
        return float(m.group(1))

    return extract("ixx"), extract("iyy"), extract("izz")


def test_inertia_orders_of_magnitude(tmp_path, monkeypatch):
    from uav_generator.exporters import flightgear
    monkeypatch.setattr(flightgear, "copy_to_flightgear", lambda *_a, **_k: None)

    root = Path(__file__).resolve().parents[2]
    yaml_path = root / "external" / "drone_spec" / "fixtures" / "uav_obs_01_ref" / "project.yaml"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    project_input = ProjectInput(**data)

    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    assert orchestrator.run()

    xml = tmp_path / "output" / "uav_obs_01" / "JSBSim" / "uav_obs_01.xml"
    assert xml.exists(), f"XML JSBSim manquant: {xml}"

    ixx, iyy, izz = _read_mass_balance_values(xml)

    assert ixx > 0
    assert iyy > 0
    assert izz > 0

    assert iyy > ixx * 0.4, f"Iyy trop faible devant Ixx: iyy={iyy}, ixx={ixx}"

    ratio_x_y = ixx / iyy
    ratio_z_y = izz / iyy
    assert ratio_x_y < 3.0, f"Anisotropie Ixx/Iyy trop forte: {ratio_x_y}"
    assert ratio_z_y < 3.0, f"Anisotropie Izz/Iyy trop forte: {ratio_z_y}"
