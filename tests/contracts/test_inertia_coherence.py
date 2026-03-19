import math
import re
from pathlib import Path


def _read_mass_balance_values(xml_path: Path) -> tuple[float, float, float]:
    text = xml_path.read_text(encoding="utf-8")

    def extract(tag: str) -> float:
        m = re.search(rf"<{tag} unit=\"SLUG\*FT2\">\s*([0-9.]+)\s*</{tag}>", text)
        assert m is not None, f"Balise {tag} introuvable dans {xml_path}"
        return float(m.group(1))

    return extract("ixx"), extract("iyy"), extract("izz")


def test_inertia_orders_of_magnitude():
    xml = Path("runtime_export/output/uav_obs_01/JSBSim/uav_obs_01.xml")
    assert xml.exists(), f"XML JSBSim manquant: {xml}"

    ixx, iyy, izz = _read_mass_balance_values(xml)

    # 1. aucune inertie n'est nulle ou négative
    assert ixx > 0
    assert iyy > 0
    assert izz > 0

    # 2. Iyy ne doit pas être écrasée artificiellement
    assert iyy > ixx * 0.4, f"Iyy trop faible devant Ixx: iyy={iyy}, ixx={ixx}"

    # 3. pas d'anisotropie absurde
    ratio_x_y = ixx / iyy
    ratio_z_y = izz / iyy
    assert ratio_x_y < 3.0, f"Anisotropie Ixx/Iyy trop forte: {ratio_x_y}"
    assert ratio_z_y < 3.0, f"Anisotropie Izz/Iyy trop forte: {ratio_z_y}"
