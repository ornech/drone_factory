import math
from typing import List
from ..data_models import (
    ProjectInput, DerivedDesign, ControlSurface, ControlSystemDesign, BlockingIssue, Gouvernes
)

def calculate_control_system(proj: ProjectInput, design: DerivedDesign) -> DerivedDesign:
    """
    Produces standard JSBSim FCS properties: left/right aileron-pos-rad, elevator-pos-rad, rudder-pos-rad.
    Conditional on empennage; signs per JSBSim convention.
    """
    surfaces: List[ControlSurface] = []
    exported_properties: List[str] = []

    MAX_DEFLECTION_DEG = 25.0  # Standard UAV limit
    max_def_rad = math.radians(MAX_DEFLECTION_DEG)

    # Roll: left/right ailerons always (differential)
    aileron_input = 'fcs/aileron-cmd-norm'
    left_output = 'fcs/left-aileron-pos-rad'
    surfaces.append(ControlSurface(
        name='left_aileron',
        input_property=aileron_input,
        output_property=left_output,
        max_deflection_rad=max_def_rad,
        sign=1.0
    ))
    exported_properties.append(left_output)

    right_output = 'fcs/right-aileron-pos-rad'
    surfaces.append(ControlSurface(
        name='right_aileron',
        input_property=aileron_input,
        output_property=right_output,
        max_deflection_rad=max_def_rad,
        sign=-1.0
    ))
    exported_properties.append(right_output)

    # Pitch/Yaw conditional on empennage and gouvernes
    # Always produce elevator/rudder for classique empennage
    if proj.contraintes.empennage in ['classique', 'en_v', 'cruciforme']:
        elevator_input = 'fcs/elevator-cmd-norm'
        elevator_output = 'fcs/elevator-pos-rad'
        surfaces.append(ControlSurface(
            name='elevator',
            input_property=elevator_input,
            output_property=elevator_output,
            max_deflection_rad=max_def_rad,
            sign=-1.0
        ))
        exported_properties.append(elevator_output)

        rudder_input = 'fcs/rudder-cmd-norm'
        rudder_output = 'fcs/rudder-pos-rad'
        surfaces.append(ControlSurface(
            name='rudder',
            input_property=rudder_input,
            output_property=rudder_output,
            max_deflection_rad=max_def_rad,
            sign=1.0
        ))
        exported_properties.append(rudder_output)

    design.control_system = ControlSystemDesign(
        surfaces=surfaces,
        exported_properties=sorted(set(exported_properties))
    )
    return design

def validate_fcs_contract(design: DerivedDesign) -> DerivedDesign:
    if not design.control_system or not design.gouvernes:
        return design

    fcs_outputs = set(design.control_system.exported_properties)
    required = set()
    if hasattr(design, 'gouvernes') and design.gouvernes and design.gouvernes.surface_ailerons_m2 > 0:
        required |= {'fcs/left-aileron-pos-rad', 'fcs/right-aileron-pos-rad'}
    if design.gouvernes.surface_profondeur_m2 > 0:
        required |= {'fcs/elevator-pos-rad'}
    if design.gouvernes.surface_derive_m2 > 0:
        required |= {'fcs/rudder-pos-rad'}

    missing = required - fcs_outputs
    if missing:
        design.blocking_issues.append(BlockingIssue(
            code="FCS_AERO_MISMATCH",
            cause=f"Aero requires FCS props not exported: {missing}",
            proposals=[]
        ))
    return design

