# uav_generator/calculators/ground.py
import math
from typing import List, Dict
from ..data_models import (
    ProjectInput, DerivedDesign, GroundReactions, VisualGeometry,
    BlockingIssue, CorrectionProposal, FuselageGeometry
)
from .. import constants as C

from typing import Tuple


def solve_tricycle_gear_analytically(
    cg_x: float,
    h_cg_above_ground: float,
    nose_load_fraction: float,
    tipback_angle_deg_target: float,
) -> Tuple[float, float, float]:
    """
    Solve deterministic tricycle gear geometry from:
    - CG longitudinal position
    - CG height above ground
    - target nose load fraction
    - target tip-back angle

    Returns:
        (main_gear_x, nose_gear_x, wheelbase)
    """
    if not (0.0 < nose_load_fraction < 1.0):
        raise ValueError("nose_load_fraction must be in ]0,1[")

    if h_cg_above_ground <= 0.0:
        raise ValueError("h_cg_above_ground must be > 0")

    if tipback_angle_deg_target <= 0.0 or tipback_angle_deg_target >= 89.0:
        raise ValueError("tipback_angle_deg_target must be in ]0,89[")

    theta = math.radians(tipback_angle_deg_target)

    # d = distance from CG to main gear
    d = h_cg_above_ground / math.tan(theta)
    main_gear_x = cg_x + d

    # nose load fraction:
    # fn = (x_main - x_cg) / (x_main - x_nose)
    nose_gear_x = main_gear_x - (main_gear_x - cg_x) / nose_load_fraction

    wheelbase = main_gear_x - nose_gear_x

    return main_gear_x, nose_gear_x, wheelbase


def solve_tricycle_gear_with_bounds(
    cg_x: float,
    h_cg_above_ground: float,
    nose_load_fraction: float,
    tipback_angle_deg_target: float,
    fuselage_length: float,
    nose_x_min: float = 0.02,
    main_x_max: float | None = None,
    wheelbase_max_ratio: float = 0.7,
) -> Tuple[float, float, float]:
    """
    Deterministic tricycle gear solver with basic geometric bounds.

    Raises ValueError if the analytically computed solution is outside
    admissible structural bounds.
    """
    x_main, x_nose, wheelbase = solve_tricycle_gear_analytically(
        cg_x=cg_x,
        h_cg_above_ground=h_cg_above_ground,
        nose_load_fraction=nose_load_fraction,
        tipback_angle_deg_target=tipback_angle_deg_target,
    )

    if main_x_max is None:
        main_x_max = fuselage_length

    if x_nose < nose_x_min:
        raise ValueError(
            f"Analytic nose gear position {x_nose:.3f} m < nose_x_min {nose_x_min:.3f} m"
        )

    if x_main > main_x_max:
        raise ValueError(
            f"Analytic main gear position {x_main:.3f} m > main_x_max {main_x_max:.3f} m"
        )

    if wheelbase > wheelbase_max_ratio * fuselage_length:
        raise ValueError(
            f"Analytic wheelbase {wheelbase:.3f} m > {wheelbase_max_ratio:.2f} * fuselage_length"
        )

    if wheelbase <= 0.0:
        raise ValueError("Analytic wheelbase must be > 0")

    return x_main, x_nose, wheelbase



def calculate_ground_systems(proj: ProjectInput, design: DerivedDesign) -> DerivedDesign:
    """
    Calculates landing gear geometry, static loads, and stability on the ground based on physical objectives.
    """
    if not all([design.mass_budget, design.wing_geometry, design.stability]):
        design.blocking_issues.append(BlockingIssue(code="GROUND_PREQ_FAIL", cause="Mass or Aero data missing.", proposals=[]))
        return design

    # --- 1. Get Inputs: Objectives, Overrides, and Key Design Data ---
    obj = proj.ground_objectifs
    ovr = proj.ground_overrides
    total_weight_n = design.mass_budget.mtow_kg * C.G
    gear_type = proj.contraintes.train
    envergure_m = design.wing_geometry.envergure_m
    mac_m = design.wing_geometry.mac_m
    wing_le_root_x = mac_m * 0.5 # Heuristic for wing root leading edge position

    # 1.1 Formalize Fuselage and CG Vertical
    if design.fuselage is None:
        # Formalize the bounding box for the aircraft body
        design.fuselage = FuselageGeometry(longueur_m=envergure_m * 0.75, maitre_couple_m=envergure_m * 0.1)
    fuselage_length = design.fuselage.longueur_m

    # --- 2. Establish Coordinate System and Key Locations ---
    # Design Frame: Origin (0,0,0) at the nose. X is backward (positive towards tail), Y is right, Z is up.
    # (Matches JSBSim structural frame convention for longitudinal axis)
    
    # Absolute CG position (longitudinal)
    cg_x = wing_le_root_x + (design.stability.cg_cible_pct_mac * design.wing_geometry.mac_m)
    cg_y = 0.0 # Assume CG is on the centerline.
    
# Vertical geometry from vertical_geometry_solver (source of truth)
    if hasattr(design, 'vertical_geometry') and design.vertical_geometry:
        vg = design.vertical_geometry
        cg_z = vg.cg_z_m
        wheel_radius_m = vg.wheel_radius_m
        gear_z_m = vg.gear_z_m
        fuselage_bottom_z_m = vg.fuselage_bottom_z_m
    else:
        # Fallback (should not happen)
        fuselage_height = design.fuselage.maitre_couple_m
        min_cg_z = -fuselage_height / 2.0 + obj.garde_sol_fuselage_m_min + 0.05
        cg_z = max(0.0, min_cg_z)
        belly_z = -fuselage_height / 2.0
        fuselage_bottom_z_m = belly_z
        wheel_radius_m = 0.05
        gear_z_m = belly_z - (abs(belly_z) + obj.garde_sol_fuselage_m_min + 0.05)
    
    design.stability.cg_location_m = [cg_x, cg_y, cg_z]

    
    # --- 3. Solve for Landing Gear Geometry ---

    # 3.1 Determine Gear Height and Wheel Radius
    # The primary driver for gear height is propeller clearance.
    prop_radius_m = (proj.helice.diametre_in * 0.0254) / 2.0
    
    # Physical vertical quantities from the vertical solver
    if hasattr(design, 'vertical_geometry') and design.vertical_geometry:
        contact_point_z = gear_z_m
        wheel_radius_m = design.vertical_geometry.wheel_radius_m
        gear_height_m = fuselage_bottom_z_m - gear_z_m
    else:
        # Fallback
        gear_height_m = abs(fuselage_bottom_z_m - gear_z_m)
        contact_point_z = gear_z_m

    # Static deflection assumption for spring calculation and visual/physical offset.
    deflection_static_m = max(0.01, wheel_radius_m * 0.3)


    # Height of CG above ground plane at rest
    h_cg_above_ground = cg_z - (fuselage_bottom_z_m - gear_z_m)
    
    if h_cg_above_ground <= 0:
        design.blocking_issues.append(BlockingIssue(
            code="NEGATIVE_CG_HEIGHT",
            cause="CG height above ground is non-positive. Aircraft would tip or scrape.",
            proposals=[]
        ))
        return design

    # 3.2 Determine Gear Positions and Wheelbase
    main_gear_x = 0.0
    nose_gear_x = 0.0
    empattement_m = 0.0

    if gear_type == "tricycle":
        # Constraint-based Optimization Solver over x_main
        best_cost = float('inf')
        best_sol = None
        
        f_target = obj.charge_nez_pct_cible / 100.0
        f_min = obj.charge_nez_pct_min / 100.0
        f_max = obj.charge_nez_pct_max / 100.0
        
        # Parse objectives
        emp_min_obj = float(obj.empattement_min_m) if str(obj.empattement_min_m).lower() != "auto" else 0.0
        
        # Parse override
        x_main_target = None
        if ovr.position_train_principal_mac_pourcent is not None:
            x_main_target = wing_le_root_x + (ovr.position_train_principal_mac_pourcent / 100.0) * mac_m
        
        # A. Analytical Bounds Formulation
        # d = distance from CG to main gear
        tipback_rad = math.radians(obj.angle_tipback_deg_min)
        d_max_tipback = h_cg_above_ground / math.tan(tipback_rad)
        
        # Analytical closure for x_nose >= 0
        # x_nose = cg_x + d * (1 - 1/fn) >= 0 => d <= cg_x / (1/fn - 1)
        # Absolute worst case uses max fn allowed
        if f_max < 1.0:
            d_max_nose = cg_x / (1.0 / f_max - 1.0)
        else:
            d_max_nose = float('inf')
            
        d_min = 0.005 # epsilon, main gear must be strictly behind CG
        
        if emp_min_obj > 0:
            # Minimum d to possibly satisfy the wheelbase constraint (d = wheelbase * fn)
            d_min = max(d_min, emp_min_obj * f_min)
            
        d_max = min(d_max_tipback, fuselage_length - cg_x, d_max_nose)
        
        
        print(f"INFO: Ground Solver - Admissible d domain: [{d_min:.3f}, {d_max:.3f}] m")
        
        if d_max < d_min:
            design.blocking_issues.append(BlockingIssue(
                code="GEAR_GEOMETRY_UNSOLVABLE",
                cause=(
                    f"Domain analytically closed. No solution possible.\n"
                    f"Max d allowed by limits (tipback/nose/fuselage) is {d_max:.3f}m, "
                    f"which is less than the strict minimum {d_min:.3f}m."
                ),
                proposals=[
                    CorrectionProposal(description="Increase max nose load target (charge_nez_pct_max).", apply_changes={}),
                    CorrectionProposal(description="Move CG further aft (reduce static margin).", apply_changes={})
                ]
            ))
            return design

        # Apply strict expert override
        if x_main_target is not None:
            d_target = x_main_target - cg_x
            if d_target < d_min or d_target > d_max:
                design.blocking_issues.append(BlockingIssue(
                    code="EXPERT_OVERRIDE_CONFLICT",
                    cause=f"Expert override position_train_principal_mac_pourcent places main gear at {x_main_target:.3f}m, which violates physical bounds [{cg_x+d_min:.3f}m, {cg_x+d_max:.3f}m].",
                    proposals=[CorrectionProposal(description="Remove or adjust 'position_train_principal_mac_pourcent'.", apply_changes={"ground_overrides.position_train_principal_mac_pourcent": None})]
                ))
                return design
            # Lock domain to the exact override target
            d_min = d_target
            d_max = d_target

        # B. Bounded Grid Search & Cost Evaluation
        steps_d = 120 if x_main_target is None else 1
        steps_f = 80
        
        for i in range(steps_d):
            d = d_min + (d_max - d_min) * (i / max(1, steps_d - 1))
            xm = cg_x + d
            
            for j in range(steps_f):
                fn = f_min + (f_max - f_min) * (j / max(1, steps_f - 1))
                
                wb = d / fn
                xn = xm - wb
                
                # Evaluate Hard Constraints
                if xn < 0.02 or xn > cg_x - 0.05: continue # Keep a tiny margin off the exact 0.0 tip
                if wb > 0.7 * fuselage_length: continue
                if emp_min_obj > 0 and wb < emp_min_obj: continue
                    
                # Evaluate Cost
                # Priority order:
                # 1. stay close to target nose load
                # 2. satisfy tip-back margin without drifting to the max nose-load bound
                # 3. keep a reasonable wheelbase ratio
                cost_f = ((fn - f_target) / max(f_target, 1e-6)) ** 2

                actual_tb = math.degrees(math.atan(h_cg_above_ground / d))
                target_tb = obj.angle_tipback_deg_min + 5.0
                cost_tb = ((actual_tb - target_tb) / max(target_tb, 1e-6)) ** 2

                cost_wb = ((wb / max(fuselage_length, 1e-6)) - 0.40) ** 2

                # Extra penalty near admissible nose-load bounds
                span_f = max(f_max - f_min, 1e-6)
                edge_penalty = min(
                    ((fn - f_min) / span_f) ** 2,
                    ((f_max - fn) / span_f) ** 2,
                )
                cost_edge = 1.0 / max(edge_penalty, 1e-6)

                cost = 50.0 * cost_f + 3.0 * cost_tb + 1.0 * cost_wb + 0.02 * cost_edge
                
                if cost < best_cost:
                    best_cost = cost
                    best_sol = {"x_main": xm, "x_nose": xn, "wb": wb, "fn": fn, "tb": actual_tb}
                    
        # C. Apply best solution
        if best_sol is None:
            design.blocking_issues.append(BlockingIssue(
                code="GEAR_GEOMETRY_UNSOLVABLE",
                cause=(
                    f"No valid solution found inside bounds. Admissible d interval was [{d_min:.2f}, {d_max:.2f}] m, "
                    f"but all configurations violated geometrical limits (x_nose, wheelbase) for the allowed load range."
                ),
                proposals=[CorrectionProposal(description="Relax load constraints or increase valid wheelbase bounds.", apply_changes={})]
            ))
            return design
            
        main_gear_x = best_sol["x_main"]
        nose_gear_x = best_sol["x_nose"]
        empattement_m = best_sol["wb"]
        cg_in_polygon = True
        print(f"INFO: Ground Solver selected - Cost: {best_cost:.3f}, x_main: {main_gear_x:.3f}m, x_nose: {nose_gear_x:.3f}m")

    else: # taildragger
        # For taildragger, main gear is AHEAD of CG.
        main_gear_dist_from_cg = h_cg_above_ground / math.tan(math.radians(obj.angle_tipback_deg_min))
        main_gear_x = cg_x - main_gear_dist_from_cg

        # Place tail wheel far back for good authority
        tail_gear_x = fuselage_length * 0.95 # Heuristic
        nose_gear_x = tail_gear_x # Use nose_gear_x variable for the third wheel
        empattement_m = tail_gear_x - main_gear_x
        cg_in_polygon = (main_gear_x < cg_x < tail_gear_x)

    nose_gear_pos = [nose_gear_x, 0, contact_point_z]

    # --- 4. Calculate Final Loads and Spring/Damping Coefficients ---
    load_nose_n = 0
    if empattement_m > 0:
        if gear_type == "tricycle":
            # Moment around main gear
            load_nose_n = total_weight_n * (main_gear_x - cg_x) / empattement_m
        else: # taildragger
            # Moment around main gear
            load_nose_n = total_weight_n * (cg_x - main_gear_x) / empattement_m

    load_main_total_n = total_weight_n - load_nose_n
    load_main_each_n = load_main_total_n / 2.0

    # 3.3 Determine Track Width (voie_m) integrating objectives and overrides
    voie_min_obj = float(obj.voie_min_m) if str(obj.voie_min_m).lower() != "auto" else 0.0
    voie_m = max(envergure_m * 0.25, voie_min_obj) # Take heuristic or objective
    
    if ovr.voie_m is not None:
        voie_m = ovr.voie_m # Strict override
        
    if voie_m < 0.1:
        design.blocking_issues.append(BlockingIssue(code="INVALID_TRACK_WIDTH", cause="Track width is physically too narrow (< 0.1m).", proposals=[]))
        return design

    # Spring constant (k) is calculated from load and desired static deflection.
    k_main_npm = load_main_each_n / deflection_static_m if deflection_static_m > 0 else 0
    c_main_nspm = 0.25 * 2 * math.sqrt(k_main_npm * (design.mass_budget.mtow_kg / 2)) # 25% critical damping

    k_nez_npm = load_nose_n / deflection_static_m if (deflection_static_m > 0 and load_nose_n > 0) else 0
    c_nez_nspm = 0.30 * 2 * math.sqrt(k_nez_npm * (design.mass_budget.mtow_kg * 0.15)) if k_nez_npm > 0 else 0

    # Friction coefficients based on runway surface
    friction_map = {
        "dur": {"static": 0.7, "dynamic": 0.5, "rolling": 0.02},
        "herbe": {"static": 0.8, "dynamic": 0.6, "rolling": 0.05},
        "terre": {"static": 0.8, "dynamic": 0.6, "rolling": 0.08},
    }
    surface_type = proj.sol_piste.revetement
    frictions = friction_map.get(surface_type, friction_map["dur"]) # Default to 'dur'

    main_gear_left_pos = [main_gear_x, -voie_m / 2, contact_point_z]
    main_gear_right_pos = [main_gear_x, voie_m / 2, contact_point_z]

    # --- 5. Structural Contact Points ---
    # Placed slightly below the gear line for protection.
    z_offset = contact_point_z - 0.05
    structural_points = [
        {"nose": [0.0, 0.0, z_offset]},
        {"tail": [cg_x + 2.0, 0.0, z_offset]}, # Far back
        {"belly_fwd": [cg_x - 0.5, 0.0, z_offset]},
        {"belly_aft": [cg_x + 0.5, 0.0, z_offset]},
        {"wingtip_l": [cg_x, -envergure_m / 2, z_offset]},
        {"wingtip_r": [cg_x, envergure_m / 2, z_offset]},
    ]
    
    # --- 6. Final Validations ---
    garde_sol_helice_m_calculee = design.vertical_geometry.prop_tip_z_m - (
        design.vertical_geometry.fuselage_bottom_z_m - design.vertical_geometry.gear_z_m
    )
    if garde_sol_helice_m_calculee <= 0.0:
        print(f"WARN: Propeller clearance marginal ({garde_sol_helice_m_calculee:.3f}m). Check propeller-clearance.md rules.")
    elif garde_sol_helice_m_calculee < obj.garde_sol_helice_m_min * 0.8:
        print(f"WARN: Propeller clearance {garde_sol_helice_m_calculee:.3f}m < 80% of target {obj.garde_sol_helice_m_min}m. Realistic for small UAV.")

    final_nose_load_fraction = load_nose_n / total_weight_n if total_weight_n > 0 else 0
    
    if not cg_in_polygon:
        proposal = CorrectionProposal(
            description="Adjust main gear position to ensure CG is within the support polygon.",
            apply_changes={}
        )
        design.blocking_issues.append(BlockingIssue(
            code="CG_OUTSIDE_SUPPORT",
            cause="The Center of Gravity is outside the landing gear support polygon. The aircraft will tip over.",
            proposals=[proposal]
        ))

    if gear_type == "tricycle" and not (obj.charge_nez_pct_min/100.0 <= final_nose_load_fraction <= obj.charge_nez_pct_max/100.0):
        proposal = CorrectionProposal(
            description=f"Adjust 'charge_nez_pct_cible' in ground_objectifs. Current target is {obj.charge_nez_pct_cible}%.",
            apply_changes={}
        )
        design.blocking_issues.append(BlockingIssue(
            code="INVALID_NOSE_GEAR_LOAD",
            cause=f"Nose gear load is {final_nose_load_fraction:.1%}, outside the required {obj.charge_nez_pct_min}-{obj.charge_nez_pct_max}% range.",
            proposals=[proposal]
        ))

    # Recalculate actual tip-back angle
    actual_tipback_angle_deg = 0
    if (main_gear_x - cg_x) > 0:
        actual_tipback_angle_deg = math.degrees(math.atan(h_cg_above_ground / (main_gear_x - cg_x)))

    # --- 7. Store Results ---
    design.ground_reactions = GroundReactions(
        charge_roue_nez_n=load_nose_n,
        charge_roue_gauche_n=load_main_each_n,
        charge_roue_droite_n=load_main_each_n,
        empattement_m=empattement_m,
        voie_m=voie_m,
        cg_dans_polygone=cg_in_polygon,
        wheel_radius_m=wheel_radius_m,
        
        # Diagnostics
        solver_d_min_m=d_min if gear_type == "tricycle" else 0.0,
        solver_d_max_m=d_max if gear_type == "tricycle" else 0.0,
        solver_cost=best_cost if gear_type == "tricycle" else 0.0,
        
        # Validation metrics
        charge_nez_pct_calculee=final_nose_load_fraction * 100.0,
        angle_tipback_deg_calcule=actual_tipback_angle_deg,
        garde_sol_helice_m_calculee=garde_sol_helice_m_calculee,
        garde_sol_fuselage_m_calculee=design.vertical_geometry.fuselage_bottom_z_m,

        nose_gear_pos=nose_gear_pos,
        main_gear_left_pos=main_gear_left_pos,
        main_gear_right_pos=main_gear_right_pos,
        
        k_nez_npm=k_nez_npm,
        c_nez_nspm=c_nez_nspm,
        k_main_npm=k_main_npm,
        c_main_nspm=c_main_nspm,
        static_friction=frictions["static"],
        dynamic_friction=frictions["dynamic"],
        rolling_friction=frictions["rolling"],
        structural_points=structural_points,
    )
    
    print(f"INFO: Ground systems calculated: Type={gear_type}, Nose Load={final_nose_load_fraction:.1%}, Tip-back={actual_tipback_angle_deg:.1f} deg")

    # Update visual geometry wheel width if available (computed after aero)
    if design.visual_geometry is not None:
        design.visual_geometry.wheel_width_m = design.ground_reactions.wheel_radius_m * 0.5

    return design
