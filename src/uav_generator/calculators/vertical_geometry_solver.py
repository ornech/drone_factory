import math
from ..data_models import ProjectInput, DerivedDesign, BlockingIssue, VerticalGeometry


def calculate_vertical_geometry(proj: ProjectInput, design: DerivedDesign) -> DerivedDesign:
    """
    Calculates coherent vertical geometry before ground solver.

    Design goal:
    - keep wheel contact coherent
    - keep fuselage above ground
    - keep propeller above ground
    - keep CG height compatible with an analytically admissible tricycle gear
      for the current ground objectives
    """

    if not (hasattr(design, "wing_geometry") and design.wing_geometry and hasattr(design, "fuselage") and design.fuselage):
        design.blocking_issues.append(
            BlockingIssue(
                code="VERT_PREQ_FAIL",
                cause="Wing or fuselage geometry missing.",
                proposals=[],
            )
        )
        return design

    wingspan_m = design.wing_geometry.envergure_m
    prop_diam_m = proj.helice.diametre_in * 0.0254
    prop_radius_m = prop_diam_m / 2.0
    obj = proj.ground_objectifs
    ovr = proj.ground_overrides

    # 1. Wheel radius
    wheel_radius_m = ovr.rayon_roue_m if ovr.rayon_roue_m else 0.05 * wingspan_m
    wheel_radius_m = max(0.04, min(0.07, wheel_radius_m))

    # 2. Gear and fuselage baseline
    gear_z_m = -wheel_radius_m
    fuselage_bottom_z_m = 0.01

    # 3. Longitudinal CG estimate used by ground admissibility
    mac_m = design.wing_geometry.mac_m
    wing_le_root_x = mac_m * 0.5
    cg_x = wing_le_root_x + (design.stability.cg_cible_pct_mac * design.wing_geometry.mac_m)

    fuselage_length = design.fuselage.longueur_m

    # 4. Ground admissibility target
    fn = obj.charge_nez_pct_cible / 100.0
    theta_deg = obj.angle_tipback_deg_min + 5.0
    theta_rad = math.radians(theta_deg)

    nose_x_min = 0.02
    wheelbase_max_ratio = 0.7
    wheelbase_max = wheelbase_max_ratio * fuselage_length
    main_x_max = fuselage_length

    # Geometric admissibility on d = x_main - x_cg
    if not (0.0 < fn < 1.0):
        design.blocking_issues.append(
            BlockingIssue(
                code="VERT_INVALID_NOSE_LOAD_TARGET",
                cause=f"Invalid nose load target {fn:.3f}.",
                proposals=[],
            )
        )
        return design

    d_max_nose = (cg_x - nose_x_min) / (1.0 / fn - 1.0)
    d_max_wb = fn * wheelbase_max
    d_max_main = main_x_max - cg_x
    d_max = min(d_max_nose, d_max_wb, d_max_main)

    if d_max <= 0.0:
        design.blocking_issues.append(
            BlockingIssue(
                code="VERT_NO_ANALYTIC_GEAR_DOMAIN",
                cause=(
                    f"No admissible tricycle gear domain from current geometry: "
                    f"d_max={d_max:.6f}."
                ),
                proposals=[],
            )
        )
        return design

    h_max = d_max * math.tan(theta_rad)

    # 5. Choose a bounded CG height above ground
    # Keep a small margin below the strict upper bound.
    h_cg_above_ground = max(0.01, 0.95 * h_max)

    cg_z_m = h_cg_above_ground + (fuselage_bottom_z_m - gear_z_m)

    # 6. Propeller geometry
    # Keep hub just high enough to avoid ground strike while staying tied to the new CG height.
    prop_hub_z_m = max(cg_z_m + 0.05, prop_radius_m + 0.02)
    prop_tip_z_m = prop_hub_z_m - prop_radius_m

    # 7. Validations
    if cg_z_m <= gear_z_m:
        design.blocking_issues.append(
            BlockingIssue(
                code="CG_BELOW_GEAR",
                cause=f"CG z={cg_z_m:.3f}m <= gear z={gear_z_m:.3f}m.",
                proposals=[],
            )
        )
        return design

    if fuselage_bottom_z_m < 0.001:
        design.blocking_issues.append(
            BlockingIssue(
                code="FUSELAGE_INTERSECT",
                cause=f"Fuselage bottom z={fuselage_bottom_z_m:.3f}m < 0.001m.",
                proposals=[],
            )
        )
        return design

    if prop_tip_z_m < 0.0:
        design.blocking_issues.append(
            BlockingIssue(
                code="PROP_GROUND_STRIKE",
                cause=f"Prop tip z={prop_tip_z_m:.3f}m < 0.",
                proposals=[],
            )
        )
        return design

    design.vertical_geometry = VerticalGeometry(
        wheel_radius_m=wheel_radius_m,
        gear_z_m=gear_z_m,
        cg_z_m=cg_z_m,
        fuselage_bottom_z_m=fuselage_bottom_z_m,
        prop_hub_z_m=prop_hub_z_m,
        prop_tip_z_m=prop_tip_z_m,
        prop_clearance_ok=(prop_tip_z_m >= obj.garde_sol_helice_m_min * 0.4),
    )

    # Keep stability Z coherent with vertical solver
    design.stability.cg_location_m[2] = cg_z_m

    print(
        f"INFO: Vertical geometry: "
        f"wheel_r={wheel_radius_m:.3f}m, "
        f"cg_z={cg_z_m:.3f}m, "
        f"h_max={h_max:.3f}m, "
        f"prop_clearance={prop_tip_z_m:.3f}m"
    )
    return design
