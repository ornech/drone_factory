# uav_generator/calculators/propulsion.py
import math
from ..data_models import ProjectInput, DerivedDesign, PowerAndBattery, BlockingIssue, CorrectionProposal
from .. import constants as C

def calculate_propulsion(proj: ProjectInput, design: DerivedDesign) -> DerivedDesign:
    """
    Refines the power, battery, and propeller calculations using a more detailed drag model.
    Validates the design against propulsion constraints.
    Follows logic from block 6.3.
    """
    if not design.mass_budget or not design.wing_geometry:
        design.blocking_issues.append(BlockingIssue(code="PROPULSION_PREQ_FAIL", cause="Mass or Aero data missing.", proposals=[]))
        return design

    # --- Extract required data from previous steps ---
    mtow_kg = design.mass_budget.mtow_kg
    S = design.wing_geometry.surface_alaire_m2
    AR = design.wing_geometry.allongement
    Vc = proj.mission.vitesse_croisiere_mps
    
    # --- 1. Refined Drag and Power Calculation ---
    
    # a) Calculate Lift Coefficient for cruise
    poids_n = mtow_kg * C.G
    CL_cruise = (2 * poids_n) / (C.RHO * (Vc**2) * S)
    
    # b) Calculate Drag Coefficient (CD = CD0 + CDi)
    CDi = (CL_cruise**2) / (math.pi * AR * C.OSWALD_EFFICIENCY_E)
    CD_cruise = C.CD0_CLEAN_AIRFRAME + CDi
    
    # c) Calculate drag force and required power
    drag_force_cruise = 0.5 * C.RHO * (Vc**2) * S * CD_cruise
    power_required_propulsive_w = drag_force_cruise * Vc
    refined_power_required_electric_w = power_required_propulsive_w / C.ETA_PROPULSIVE_CRUISE

    # --- 2. Validation Checks ---

    # a) Check if motor continuous power is sufficient
    if refined_power_required_electric_w > proj.propulsion.puissance_continue_w:
        design.blocking_issues.append(BlockingIssue(
            code="INSUFFICIENT_CRUISE_POWER",
            cause=(
                f"Refined cruise power required ({refined_power_required_electric_w:.0f}W) "
                f"exceeds motor's continuous power ({proj.propulsion.puissance_continue_w}W)."
            ),
            proposals=[
                CorrectionProposal(
                    description=f"Select a motor with at least {refined_power_required_electric_w:.0f}W continuous power.",
                    apply_changes={"propulsion.puissance_continue_w": int(refined_power_required_electric_w * 1.15)}
                )
            ]
        ))

    # b) Check if the battery mass allocated in the mass budget is sufficient
    endurance_h = proj.mission.endurance_min / 60.0
    energy_required_wh = (refined_power_required_electric_w * endurance_h) / C.BATTERY_USABLE_CAPACITY_FRACTION
    required_battery_mass_kg = energy_required_wh / C.BATTERY_ENERGY_DENSITY_WH_KG
    allocated_battery_mass_kg = design.mass_budget.masse_batterie_kg

    if required_battery_mass_kg > allocated_battery_mass_kg:
        overweight_fraction = required_battery_mass_kg / allocated_battery_mass_kg
        design.blocking_issues.append(BlockingIssue(
            code="BATTERY_MASS_INSUFFICIENT",
            cause=(
                f"Required battery mass for endurance ({required_battery_mass_kg:.2f} kg) "
                f"exceeds the allocated mass budget ({allocated_battery_mass_kg:.2f} kg). "
                "This indicates the initial L/D estimate in the mass calculator was too optimistic."
            ),
            proposals=[
                CorrectionProposal(
                    description=f"Reduce mission endurance by ~{overweight_fraction:.0%}.",
                    apply_changes={"mission.endurance_min": int(proj.mission.endurance_min / overweight_fraction)}
                ),
            ]
        ))

    # --- 3. Propeller & Motor RPM Calculation ---
    
    # a) Estimate RPM from cruise speed and pitch (kinematic)
    pitch_m = proj.helice.pas_in * 0.0254
    # Assume propeller slip, i.e., it's not a perfect screw
    effective_pitch_advance_ratio = 0.8
    
    regime_croisiere_rpm = (Vc / (pitch_m * effective_pitch_advance_ratio)) * 60 if pitch_m > 0 else 0

    # b) Check against motor's theoretical max RPM
    kv = proj.propulsion.kv_moteur
    voltage = proj.propulsion.tension_batterie_v
    regime_max_rpm_no_load = kv * voltage
    
    if regime_croisiere_rpm > regime_max_rpm_no_load * 0.9: # Check if cruise RPM is too close to max
        design.blocking_issues.append(BlockingIssue(
            code="RPM_TOO_HIGH",
            cause=f"Estimated cruise RPM ({regime_croisiere_rpm:.0f}) is too high for the motor ({kv} KV @ {voltage}V).",
            proposals=[
                CorrectionProposal(description="Increase propeller pitch to reduce RPM for the same speed.", apply_changes={"helice.pas_in": proj.helice.pas_in + 1}),
                CorrectionProposal(description="Decrease motor KV or increase battery voltage.", apply_changes={"propulsion.kv_moteur": int(kv * 0.8)})
            ]
        ))

    # --- 4. Static Thrust Estimation ---
    prop_diam_m = proj.helice.diametre_in * 0.0254
    prop_area = math.pi * (prop_diam_m / 2)**2
    # Standard static thrust formula based on power
    poussee_statique_estimee_n = (
        (proj.propulsion.puissance_max_w * C.ETA_PROPULSIVE_STATIC)**(2/3) *
        (2 * C.RHO * prop_area)**(1/3)
    )
    
    TWR = poussee_statique_estimee_n / poids_n
    if TWR < C.MIN_TWR_STATIC:
        design.blocking_issues.append(BlockingIssue(
            code="LOW_TWR",
            cause=f"Static Thrust-to-Weight Ratio is too low ({TWR:.2f}). Takeoff performance will be poor. Aim for > {C.MIN_TWR_STATIC}.",
            proposals=[
                CorrectionProposal(description="Increase motor max power.", apply_changes={"propulsion.puissance_max_w": int(proj.propulsion.puissance_max_w * 1.5)}),
                CorrectionProposal(description="Increase propeller diameter for more thrust.", apply_changes={"helice.diametre_in": proj.helice.diametre_in + 2})
            ]
        ))

    # --- 5. Finalize Output ---
    design.power_and_battery = PowerAndBattery(
        puissance_requise_croisiere_w=refined_power_required_electric_w,
        capacite_batterie_ah=energy_required_wh / voltage,
        poussee_statique_estimee_n=poussee_statique_estimee_n,
        regime_croisiere_rpm=regime_croisiere_rpm,
        regime_max_rpm=regime_max_rpm_no_load,
    )
    
    print(f"INFO: Propulsion refined: Cruise Power={refined_power_required_electric_w:.0f}W, Static TWR={TWR:.2f}")

    return design
