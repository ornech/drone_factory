from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator import constants as C


def test_mass_budget_sensitivity(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"
    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    proj = ProjectInput(**data)

    for factor in [2.0, 1.5, 1.2, 1.0, 0.8]:
        monkeypatch.setattr(C, "PROPULSION_SYSTEM_MASS_FACTOR_G_PER_W", factor)
        design = DerivedDesign()
        design = calculate_mass_budget(proj, design)
        mb = design.mass_budget
        print(
            f"factor={factor:.1f} "
            f"mtow={mb.mtow_kg:.6f} "
            f"empty={mb.masse_vide_kg:.6f} "
            f"battery={mb.masse_batterie_kg:.6f}"
        )
