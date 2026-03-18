# uav_generator/calculators/aerodynamics.py

import math
from ..data_models import ProjectInput, DerivedDesign, WingGeometry, Stability, Empennages, Gouvernes, FuselageGeometry, VisualGeometry, BlockingIssue, CorrectionProposal


def calculate_aero(proj: ProjectInput, design: DerivedDesign) -> DerivedDesign:
    """
    Calculates the main aerodynamic parameters of the wing, empennages, and control surfaces.
    
    Follows the logic from block 6.2 of the prompt.
    """
    # This calculator requires the mass budget to be calculated first.
    if not design.mass_budget or not design.mass_budget.mtow_kg:
        # This should not happen if the pipeline is correct.
        issue = BlockingIssue(
            code="MASS_BUDGET_MISSING",
            cause="Mass budget must be calculated before aerodynamics.",
            proposals=[]
        )
        design.blocking_issues.append(issue)
        return design

    # --- Assumptions / Heuristics (could be moved to an expert config) ---
    RHO = 1.225  # Air density at sea level, kg/m^3
    G = 9.81
    # Assumed design max lift coefficient for a typical airfoil with flaps/slats implicitly considered in Vstall.
    CLMAX_DESIGN = 1.4
    AR_TARGET = 8.0     # Target aspect ratio, typical for observation UAVs.
    TAPER_RATIO = 0.5   # Lambda, wing taper ratio.
    STATIC_MARGIN_TARGET = 0.10 # Target static margin (10% of MAC). Positive means stable.
    # Tail Volume Coefficients
    C_H = 0.8  # Horizontal tail volume coefficient
    C_V = 0.05 # Vertical tail volume coefficient
    
    # Control surface area fractions
    AILERON_CHORD_FRACTION = 0.25
    ELEVATOR_CHORD_FRACTION = 0.30
    RUDDER_CHORD_FRACTION = 0.30


    # 1. Wing Area Calculation
    W = design.mass_budget.mtow_kg * G
    # Heuristic: Stall speed is roughly Takeoff speed / 1.2
    V_stall = proj.mission.vitesse_decollage_mps_max / 1.2
    
    if V_stall <= 0:
        design.blocking_issues.append(BlockingIssue(
            code="INVALID_STALL_SPEED",
            cause=f"Stall speed ({V_stall:.2f} m/s) must be positive. Check 'vitesse_decollage_mps_max'.",
            proposals=[CorrectionProposal(description="Set a realistic 'vitesse_decollage_mps_max' > 0.", apply_changes={"mission.vitesse_decollage_mps_max": 14.0})]
        ))
        return design # Cannot proceed.

    surface_alaire_m2 = (2 * W) / (RHO * (V_stall**2) * CLMAX_DESIGN)

    # 2. Wingspan and Chord Calculation
    # Start with the target AR, but cap it at the max wingspan constraint.
    envergure_m = math.sqrt(AR_TARGET * surface_alaire_m2)
    if envergure_m > proj.contraintes.envergure_max_m:
        envergure_m = proj.contraintes.envergure_max_m
        # This is a note for now, could become a formal warning.
        print(f"WARN: Wingspan capped by constraint ({envergure_m:.2f}m). Effective Aspect Ratio will be lower than target.")

    allongement = (envergure_m**2) / surface_alaire_m2
    
    corde_racine_m = (2 * surface_alaire_m2) / (envergure_m * (1 + TAPER_RATIO))
    corde_saumon_m = TAPER_RATIO * corde_racine_m
    mac_m = (2/3) * corde_racine_m * (1 + TAPER_RATIO + TAPER_RATIO**2) / (1 + TAPER_RATIO)

    # Fuselage created in aero for vertical solver pre-req
    if not design.fuselage:
        design.fuselage = FuselageGeometry(longueur_m=envergure_m * 0.75, maitre_couple_m=envergure_m * 0.1)
    
    design.wing_geometry = WingGeometry(
        surface_alaire_m2=surface_alaire_m2,
        envergure_m=envergure_m,
        allongement=allongement,
        corde_racine_m=corde_racine_m,
        corde_saumon_m=corde_saumon_m,
        mac_m=mac_m,
        profil_racine="NACA2412", # Suggest a common, well-behaved airfoil for the wing
        profil_saumon="NACA4412", # Can be different at the tip
    )


    # 3. CG Target and Stability
    # A simple assumption: Neutral Point is at 35% of MAC for a conventional aircraft.
    # A better model would calculate this based on wing/tail geometry and positions.
    np_estime_pct_mac = 0.35 
    cg_cible_pct_mac = np_estime_pct_mac - STATIC_MARGIN_TARGET

    if cg_cible_pct_mac < 0 or cg_cible_pct_mac > np_estime_pct_mac:
        design.blocking_issues.append(BlockingIssue(
            code="UNSTABLE_CG",
            cause=f"The calculated CG target ({cg_cible_pct_mac:.2%}) is behind the neutral point ({np_estime_pct_mac:.2%}). The aircraft would be statically unstable.",
            proposals=[CorrectionProposal(description="Increase the target static margin.", apply_changes={})]
        ))

    design.stability = Stability(
        cg_cible_pct_mac=cg_cible_pct_mac,
        marge_statique_pct=STATIC_MARGIN_TARGET,
        point_neutre_estime_pct_mac=np_estime_pct_mac,
    )
    
    # 4. Empennages (Tail Surfaces)
    # Refined lever arm estimation: typically 2.5 to 4 times the MAC.
    l_H = 3.0 * mac_m # Horizontal tail lever arm
    l_V = 3.0 * mac_m # Vertical tail lever arm

    surface_h_m2 = (C_H * surface_alaire_m2 * mac_m) / l_H if l_H > 0 else 0
    surface_v_m2 = (C_V * surface_alaire_m2 * envergure_m) / l_V if l_V > 0 else 0

    if surface_h_m2 <= 0 or surface_v_m2 <= 0:
        design.blocking_issues.append(BlockingIssue(
            code="ZERO_TAIL_SURFACE",
            cause="Calculated horizontal or vertical tail surface is zero or negative. Check calculation parameters.",
            proposals=[]
        ))

    design.empennages = Empennages(surface_h_m2=surface_h_m2, surface_v_m2=surface_v_m2)

    # 5. Gouvernes (Control Surfaces)
    # Areas are estimated as a fraction of the parent surface.
    surface_ailerons_m2 = surface_alaire_m2 * 0.08 # Ailerons are part of the wing
    surface_profondeur_m2 = surface_h_m2 * ELEVATOR_CHORD_FRACTION
    surface_derive_m2 = surface_v_m2 * RUDDER_CHORD_FRACTION
    
    if surface_ailerons_m2 <= 0 or surface_profondeur_m2 <= 0 or surface_derive_m2 <= 0:
         design.blocking_issues.append(BlockingIssue(
            code="INSUFFICIENT_CONTROL_SURFACE",
            cause="One or more control surfaces have zero or negative area. This usually follows a zero-sized tail surface.",
            proposals=[]
        ))

    design.gouvernes = Gouvernes(
        surface_ailerons_m2=surface_ailerons_m2,
        surface_profondeur_m2=surface_profondeur_m2,
        surface_derive_m2=surface_derive_m2,
    )

    # Compute visual geometry
    wg = design.wing_geometry
    emp = design.empennages
    htail_span_m = math.sqrt(emp.surface_h_m2 * 3.0)
    htail_chord_root_m = emp.surface_h_m2 / htail_span_m
    htail_chord_tip_m = htail_chord_root_m * 0.8
    design.visual_geometry = VisualGeometry(
        fuselage_length_m=wg.envergure_m * 0.7,
        fuselage_width_m=wg.corde_racine_m * 0.8,
        fuselage_height_m=wg.corde_racine_m * 1.0,
        wing_root_le_x_m=wg.mac_m * 0.5,
        wing_z_m=wg.corde_racine_m * 1.0,
        htail_arm_x_m=3.0 * wg.mac_m,
        htail_span_m=htail_span_m,
        htail_chord_root_m=htail_chord_root_m,
        htail_chord_tip_m=htail_chord_tip_m,
        htail_z_m=wg.corde_racine_m * 1.0 * 0.8,
        wheel_width_m=None
    )

    print(f"INFO: Aero calculated: Wing Area={surface_alaire_m2:.2f} m^2, Span={envergure_m:.2f} m, CG @ {cg_cible_pct_mac:.1%}")
    return design
