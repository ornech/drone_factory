from pathlib import Path
import yaml
import pytest

from uav_generator.data_models import ProjectInput, DerivedDesign
from uav_generator.calculators.mass import calculate_mass_budget
from uav_generator.calculators.control_system import calculate_control_system
from uav_generator.calculators.aerodynamics import calculate_aero
from uav_generator.calculators.vertical_geometry_solver import calculate_vertical_geometry
from uav_generator.calculators.propulsion import calculate_propulsion
from uav_generator.calculators.ground import calculate_ground_systems


def test_ground_reactions_respect_physical_contract():
    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    proj = ProjectInput(**data)
    design = DerivedDesign()

    design = calculate_mass_budget(proj, design)
    design = calculate_control_system(proj, design)
    design = calculate_aero(proj, design)
    design = calculate_vertical_geometry(proj, design)
    design = calculate_propulsion(proj, design)
    design = calculate_ground_systems(proj, design)

    gr = design.ground_reactions
    vg = design.vertical_geometry
    assert gr is not None
    assert vg is not None

    cg_x = design.stability.cg_location_m[0]

    # 1. géométrie générale du train
    assert gr.empattement_m > 0.05
    assert gr.voie_m > 0.1

    # 2. charge nez dans l’intervalle demandé par les objectifs
    assert proj.ground_objectifs.charge_nez_pct_min <= gr.charge_nez_pct_calculee <= proj.ground_objectifs.charge_nez_pct_max

    # 3. angle de tip-back admissible
    assert gr.angle_tipback_deg_calcule >= proj.ground_objectifs.angle_tipback_deg_min

    # 4. garde au sol hélice non négative
    assert gr.garde_sol_helice_m_calculee >= 0.0

    # 5. cohérence longitudinale
    assert gr.nose_gear_pos[0] >= 0.02
    assert gr.main_gear_left_pos[0] > cg_x
    assert gr.main_gear_right_pos[0] > cg_x

    # 6. symétrie du train principal
    assert gr.main_gear_left_pos[0] == pytest.approx(gr.main_gear_right_pos[0], abs=1e-9)
    assert gr.main_gear_left_pos[1] == pytest.approx(-gr.main_gear_right_pos[1], abs=1e-9)
    assert gr.main_gear_left_pos[2] == pytest.approx(gr.main_gear_right_pos[2], abs=1e-9)

    # 7. cohérence verticale avec le solver vertical
    ground_plane_z = vg.fuselage_bottom_z_m - vg.gear_z_m
    rebuilt_prop_clearance = vg.prop_tip_z_m - ground_plane_z
    assert gr.garde_sol_helice_m_calculee == pytest.approx(rebuilt_prop_clearance, abs=1e-9)

    rebuilt_tipback = pytest.approx(gr.angle_tipback_deg_calcule, abs=1e-9)
    assert rebuilt_tipback == gr.angle_tipback_deg_calcule
