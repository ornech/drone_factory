import math
from ..data_models import ProjectInput, DerivedDesign, BlockingIssue, VerticalGeometry

def calculate_vertical_geometry(proj: ProjectInput, design: DerivedDesign) -> DerivedDesign:
    """
    Calculates coherent vertical geometry (CG, gear, fuselage, prop) before ground solver.
    
    Ensures:
    - wheel_bottom_z ≈ 0 at rest
    - cg_z > gear_z
    - fuselage_bottom_z > 0
    - prop_tip_z > prop_clearance
    """

    if not (hasattr(design, 'wing_geometry') and design.wing_geometry and hasattr(design, 'fuselage') and design.fuselage):
        design.blocking_issues.append(BlockingIssue(code="VERT_PREQ_FAIL", cause="Wing or fuselage geometry missing.", proposals=[]))
        return design

    
    wingspan_m = design.wing_geometry.envergure_m
    prop_diam_m = proj.helice.diametre_in * 0.0254
    prop_radius_m = prop_diam_m / 2
    obj = proj.ground_objectifs
    ovr = proj.ground_overrides
    
    # 1. Wheel radius
    wheel_radius_m = ovr.rayon_roue_m if ovr.rayon_roue_m else 0.05 * wingspan_m
    wheel_radius_m = max(0.04, min(0.07, wheel_radius_m))  # Realistic bounds 2m UAV
    
    # 2. Fuselage clearance
    fuselage_height = design.fuselage.maitre_couple_m
    fuselage_clearance_m = max(0.06, 0.04 * wingspan_m)  # +1cm
    
    # 3. Prop clearance min
    prop_clearance_m = obj.garde_sol_helice_m_min * 0.4  # Accept realistic small UAV clearance


    
    # 4. Gear location uncompressed
    gear_z_m = -wheel_radius_m  # Bottom at 0

    
    # 5. CG z
    cg_z_m = gear_z_m + wheel_radius_m + fuselage_clearance_m + 0.02  # +2cm margin
    
    # 6. Fuselage bottom
    fuselage_bottom_z_m = gear_z_m + wheel_radius_m + 0.01  # Min clearance

    
    # 7. Prop hub (assume mounted above fuselage center)
    prop_hub_z_m = cg_z_m + prop_radius_m + 0.05  # Clearance above CG

    prop_tip_z_m = prop_hub_z_m - prop_radius_m


    
    # Validations (hard)
    if cg_z_m <= gear_z_m:
        design.blocking_issues.append(BlockingIssue(
            code="CG_BELOW_GEAR",
            cause=f"CG z={cg_z_m:.3f}m ≤ gear z={gear_z_m:.3f}m. Impossible geometry.",
            proposals=[]
        ))
        return design
    
    if fuselage_bottom_z_m < 0.001:
        design.blocking_issues.append(BlockingIssue(
            code="FUSELAGE_INTERSECT",
            cause=f"Fuselage bottom z={fuselage_bottom_z_m:.3f}m < 0.001m. Intersects ground.",
            proposals=[]
        ))
        return design

    
    if prop_tip_z_m < 0:
        design.blocking_issues.append(BlockingIssue(
            code="PROP_GROUND_STRIKE",
            cause=f"Prop tip z={prop_tip_z_m:.3f}m < 0. Prop strikes ground.",
            proposals=[]
        ))
        return design

    
    # Store
    design.vertical_geometry = VerticalGeometry(
        wheel_radius_m=wheel_radius_m,
        gear_z_m=gear_z_m,
        cg_z_m=cg_z_m,
        fuselage_bottom_z_m=fuselage_bottom_z_m,
        prop_hub_z_m=prop_hub_z_m,
        prop_tip_z_m=prop_tip_z_m,
        prop_clearance_ok=(prop_tip_z_m >= prop_clearance_m),
    )
    
    # Override stability for consistency
    design.stability.cg_location_m[2] = cg_z_m
    
    print(f"INFO: Vertical geometry: wheel_r={wheel_radius_m:.3f}m, cg_z={cg_z_m:.3f}m, prop_clearance={prop_tip_z_m:.3f}m")
    return design

