# uav_generator/calculators/mass.py
import math
from ..data_models import ProjectInput, DerivedDesign, MassBudget, BlockingIssue, CorrectionProposal
from .. import constants as C

# Heuristics for airframe mass fraction based on construction material
# (Masse Vide - (Masse Moteur + Masse Batterie)) / MTOW
AIRFRAME_MASS_FRACTION = {
    "mousse_composite": 0.25,
    "fibre_verre": 0.30,
    "fibre_carbone": 0.22,
    "default": 0.28
}


def get_airframe_mass_fraction(proj: ProjectInput) -> float:
    """Returns an estimated airframe mass fraction based on construction material."""
    material = proj.construction.materiau
    return AIRFRAME_MASS_FRACTION.get(material, AIRFRAME_MASS_FRACTION["default"])


def calculate_mass_budget(proj: ProjectInput, design: DerivedDesign) -> DerivedDesign:
    """
    Calculates the mass budget iteratively, as battery mass and MTOW are interdependent.
    """
    charge_utile_kg = proj.mission.charge_utile_kg
    endurance_h = proj.mission.endurance_min / 60.0
    v_croisiere_mps = proj.mission.vitesse_croisiere_mps
    max_power_w = proj.propulsion.puissance_max_w

    # --- Initial Guesses ---
    # Estimate propulsion system mass (motor, controller, wiring) from max power
    masse_propulsion_kg = (max_power_w * C.PROPULSION_SYSTEM_MASS_FACTOR_G_PER_W) / 1000.0

    # Initial MTOW guess based on payload fraction (common for observation UAVs)
    payload_fraction_guess = 0.25
    mtow_iter_kg = charge_utile_kg / payload_fraction_guess

    # --- Iteration to find a stable MTOW ---
    masse_batterie_kg = 0
    airframe_fraction = get_airframe_mass_fraction(proj)

    # Assumed Lift-to-Drag ratio for this initial estimation loop
    L_D_RATIO_ESTIMATED = 12.0

    for i in range(10): # Iterate to converge on a stable MTOW
        # 1. Estimate airframe mass based on the current MTOW guess
        masse_vide_kg = mtow_iter_kg * airframe_fraction

        # 2. Recalculate total weight (excluding battery)
        current_mass_without_battery = masse_vide_kg + masse_propulsion_kg + charge_utile_kg
        
        # 3. Estimate required power and energy based on current MTOW
        poids_n = mtow_iter_kg * C.G
        poussee_requise_croisiere_n = poids_n / L_D_RATIO_ESTIMATED
        
        puissance_requise_meca_w = poussee_requise_croisiere_n * v_croisiere_mps
        puissance_requise_elec_w = puissance_requise_meca_w / C.ETA_PROPULSIVE_CRUISE
        
        # 4. Calculate required battery energy and mass
        energie_requise_wh = (puissance_requise_elec_w * endurance_h) / C.BATTERY_USABLE_CAPACITY_FRACTION
        masse_batterie_kg = energie_requise_wh / C.BATTERY_ENERGY_DENSITY_WH_KG
        
        # 5. Calculate the new MTOW with the updated battery mass
        new_mtow_kg = current_mass_without_battery + masse_batterie_kg

        # Check for convergence
        if abs(new_mtow_kg - mtow_iter_kg) < 0.01:
            mtow_iter_kg = new_mtow_kg
            break
        
        mtow_iter_kg = new_mtow_kg
    else:
        print("WARN: Mass calculation did not converge after 10 iterations.")

    # --- Finalization and Validation ---
    final_mtow = mtow_iter_kg
    final_masse_vide = final_mtow * airframe_fraction
    final_total_empty_mass = final_masse_vide + masse_propulsion_kg

    mtow_max_contrainte_kg = proj.contraintes.masse_max_decollage_kg
    if final_mtow > mtow_max_contrainte_kg:
        overweight_kg = final_mtow - mtow_max_contrainte_kg
        design.blocking_issues.append(BlockingIssue(
            code="MTOW_CONSTRAINT_EXCEEDED",
            cause=(
                f"Calculated MTOW ({final_mtow:.2f} kg) exceeds max constraint ({mtow_max_contrainte_kg:.2f} kg) by {overweight_kg:.2f} kg."
            ),
            proposals=[
                CorrectionProposal(
                    description=f"Increase max takeoff weight to at least {math.ceil(final_mtow)} kg.",
                    apply_changes={"contraintes.masse_max_decollage_kg": math.ceil(final_mtow)}
                ),
                CorrectionProposal(
                    description=f"Reduce payload mass by {overweight_kg:.2f} kg.",
                    apply_changes={"mission.charge_utile_kg": proj.mission.charge_utile_kg - overweight_kg}
                )
            ]
        ))

    design.mass_budget = MassBudget(
        mtow_kg=final_mtow,
        masse_vide_kg=final_total_empty_mass,
        masse_batterie_kg=masse_batterie_kg,
        masse_charge_utile_kg=charge_utile_kg
    )
    
    # Pass the initial power estimate to the propulsion block for refinement

    print(f"INFO: Mass budget calculated: MTOW={final_mtow:.2f} kg "
          f"(Empty: {final_total_empty_mass:.2f}, "
          f"Battery: {masse_batterie_kg:.2f}, "
          f"Payload: {charge_utile_kg:.2f})")

    return design
