from pathlib import Path
import yaml

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators import mass as mass_module


def test_mass_budget_airframe_fraction_sensitivity(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"
    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    proj = ProjectInput(**data)

    for fraction in [0.25, 0.23, 0.22, 0.21, 0.20]:
        monkeypatch.setattr(mass_module, "get_airframe_mass_fraction", lambda _proj, f=fraction: f)
        design = DerivedDesign()
        design = mass_module.calculate_mass_budget(proj, design)
        mb = design.mass_budget
        print(
            f"fraction={fraction:.2f} "
            f"mtow={mb.mtow_kg:.6f} "
            f"empty={mb.masse_vide_kg:.6f} "
            f"battery={mb.masse_batterie_kg:.6f}"
        )
