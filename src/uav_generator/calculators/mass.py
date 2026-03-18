import math

from ..data_models import (
    BlockingIssue,
    CorrectionProposal,
    DerivedDesign,
    MassBudget,
    ProjectInput,
)
from .. import constants as C


AIRFRAME_STRUCTURE_FRACTION = {
    "mousse_composite": 0.25,
    "fibre_verre": 0.30,
    "fibre_carbone": 0.22,
    "default": 0.28,
}


def get_airframe_structure_fraction(proj: ProjectInput) -> float:
    material = proj.construction.materiau
    return AIRFRAME_STRUCTURE_FRACTION.get(
        material,
        AIRFRAME_STRUCTURE_FRACTION["default"],
    )


def estimate_propulsion_system_mass_kg(max_power_w: float) -> float:
    return (max_power_w * C.PROPULSION_SYSTEM_MASS_FACTOR_G_PER_W) / 1000.0


def estimate_required_battery_mass_kg(
    mtow_guess_kg: float,
    cruise_speed_mps: float,
    endurance_h: float,
    l_d_ratio_estimated: float,
) -> float:
    weight_n = mtow_guess_kg * C.G
    cruise_thrust_required_n = weight_n / l_d_ratio_estimated
    cruise_mechanical_power_w = cruise_thrust_required_n * cruise_speed_mps
    cruise_electrical_power_w = cruise_mechanical_power_w / C.ETA_PROPULSIVE_CRUISE
    required_energy_wh = (
        cruise_electrical_power_w * endurance_h
    ) / C.BATTERY_USABLE_CAPACITY_FRACTION
    return required_energy_wh / C.BATTERY_ENERGY_DENSITY_WH_KG


def calculate_mass_budget(proj: ProjectInput, design: DerivedDesign) -> DerivedDesign:
    payload_mass_kg = proj.mission.charge_utile_kg
    endurance_h = proj.mission.endurance_min / 60.0
    cruise_speed_mps = proj.mission.vitesse_croisiere_mps
    max_power_w = proj.propulsion.puissance_max_w

    structure_fraction = get_airframe_structure_fraction(proj)
    propulsion_mass_kg = estimate_propulsion_system_mass_kg(max_power_w)

    payload_fraction_guess = 0.25
    mtow_guess_kg = payload_mass_kg / payload_fraction_guess
    l_d_ratio_estimated = 12.0

    battery_mass_kg = 0.0

    for _ in range(10):
        structure_mass_kg = mtow_guess_kg * structure_fraction
        empty_mass_exported_kg = structure_mass_kg + propulsion_mass_kg
        mass_without_battery_kg = empty_mass_exported_kg + payload_mass_kg

        battery_mass_kg = estimate_required_battery_mass_kg(
            mtow_guess_kg=mtow_guess_kg,
            cruise_speed_mps=cruise_speed_mps,
            endurance_h=endurance_h,
            l_d_ratio_estimated=l_d_ratio_estimated,
        )

        new_mtow_kg = mass_without_battery_kg + battery_mass_kg

        if abs(new_mtow_kg - mtow_guess_kg) < 0.01:
            mtow_guess_kg = new_mtow_kg
            break

        mtow_guess_kg = new_mtow_kg
    else:
        print("WARN: Mass calculation did not converge after 10 iterations.")

    final_mtow_kg = mtow_guess_kg
    final_structure_mass_kg = final_mtow_kg * structure_fraction
    final_empty_mass_exported_kg = final_structure_mass_kg + propulsion_mass_kg

    mtow_limit_kg = proj.contraintes.masse_max_decollage_kg
    if final_mtow_kg > mtow_limit_kg:
        overweight_kg = final_mtow_kg - mtow_limit_kg
        design.blocking_issues.append(
            BlockingIssue(
                code="MTOW_CONSTRAINT_EXCEEDED",
                cause=(
                    f"Calculated MTOW ({final_mtow_kg:.2f} kg) exceeds max constraint "
                    f"({mtow_limit_kg:.2f} kg) by {overweight_kg:.2f} kg."
                ),
                proposals=[
                    CorrectionProposal(
                        description=(
                            f"Increase max takeoff weight to at least {math.ceil(final_mtow_kg)} kg."
                        ),
                        apply_changes={
                            "contraintes.masse_max_decollage_kg": math.ceil(final_mtow_kg)
                        },
                    ),
                    CorrectionProposal(
                        description=f"Reduce payload mass by {overweight_kg:.2f} kg.",
                        apply_changes={
                            "mission.charge_utile_kg": proj.mission.charge_utile_kg - overweight_kg
                        },
                    ),
                ],
            )
        )

    design.mass_budget = MassBudget(
        mtow_kg=final_mtow_kg,
        masse_vide_kg=final_empty_mass_exported_kg,
        masse_batterie_kg=battery_mass_kg,
        masse_charge_utile_kg=payload_mass_kg,
    )

    print(
        f"INFO: Mass budget calculated: MTOW={final_mtow_kg:.2f} kg "
        f"(Empty: {final_empty_mass_exported_kg:.2f}, "
        f"Battery: {battery_mass_kg:.2f}, "
        f"Payload: {payload_mass_kg:.2f})"
    )

    return design
