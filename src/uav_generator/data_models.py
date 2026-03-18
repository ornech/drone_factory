# uav_generator/data_models.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Union

# ==============================================================================
# 1. Input Schema (Mirrors project.yaml)
# ==============================================================================

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ProjectInfo(StrictBaseModel):
    nom: str
    description: str

class Mission(StrictBaseModel):
    charge_utile_kg: float
    endurance_min: int
    vitesse_croisiere_mps: float
    vitesse_max_mps: float
    vitesse_decollage_mps_max: float
    distance_decollage_m_max: int
    altitude_operation_m: int
    type_mission: str

class Contraintes(StrictBaseModel):
    envergure_max_m: float
    masse_max_decollage_kg: float
    mode_depart: str
    configuration: str
    empennage: str
    train: str

class GroundObjectifs(StrictBaseModel):
    charge_nez_pct_cible: float
    charge_nez_pct_min: float
    charge_nez_pct_max: float
    angle_tipback_deg_min: float
    garde_sol_helice_m_min: float
    garde_sol_fuselage_m_min: float
    voie_min_m: Union[str, float] # 'auto' or float
    empattement_min_m: Union[str, float] # 'auto' or float

class GroundOverrides(StrictBaseModel):
    position_train_principal_mac_pourcent: Optional[float] = None
    voie_m: Optional[float] = None
    rayon_roue_m: Optional[float] = None

class Propulsion(StrictBaseModel):
    type_moteur: str
    puissance_continue_w: int
    puissance_max_w: int
    tension_batterie_v: float
    kv_moteur: int
    nb_moteurs: int

class Helice(StrictBaseModel):
    diametre_in: int
    pas_in: int
    nb_pales: int

class SolPiste(StrictBaseModel):
    roulage_requis: bool
    revetement: str
    directionnel_au_sol: str
    vent_travers_kt_max: int

class Construction(StrictBaseModel):
    materiau: str
    priorite: str

class ProjectInput(StrictBaseModel):
    projet: ProjectInfo
    mission: Mission
    contraintes: Contraintes
    ground_objectifs: GroundObjectifs
    ground_overrides: GroundOverrides
    propulsion: Propulsion
    helice: Helice
    sol_piste: SolPiste
    construction: Construction

# ==============================================================================
# 2. Correction & Issue Schema
# ==============================================================================

class CorrectionProposal(StrictBaseModel):
    description: str
    # The key is a dot-separated path to the attribute in ProjectInput
    # e.g., "contraintes.train_main_x_m"
    apply_changes: Dict[str, Any]

class BlockingIssue(StrictBaseModel):
    code: str  # e.g., "CG_OUTSIDE_SUPPORT"
    cause: str
    proposals: List[CorrectionProposal]

# ==============================================================================
# 3. Derived Design Schema (Internal State & Final Output)
# ==============================================================================

# These models will be populated by the calculator modules

class MassBudget(StrictBaseModel):
    mtow_kg: float
    masse_vide_kg: float
    masse_batterie_kg: float
    masse_charge_utile_kg: float

class WingGeometry(StrictBaseModel):
    surface_alaire_m2: float
    envergure_m: float
    allongement: float
    corde_racine_m: float
    corde_saumon_m: float
    mac_m: float
    profil_racine: str
    profil_saumon: str

class Stability(StrictBaseModel):
    cg_cible_pct_mac: float
    marge_statique_pct: float
    point_neutre_estime_pct_mac: float
    cg_location_m: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0]) # [x, y, z] in design frame

class Empennages(StrictBaseModel):
    surface_h_m2: float
    surface_v_m2: float
    
class FuselageGeometry(StrictBaseModel):
    longueur_m: float
    maitre_couple_m: float

class Gouvernes(StrictBaseModel):
    surface_ailerons_m2: float
    surface_profondeur_m2: float
    surface_derive_m2: float

class PowerAndBattery(StrictBaseModel):
    puissance_requise_croisiere_w: float
    capacite_batterie_ah: float
    poussee_statique_estimee_n: float
    regime_croisiere_rpm: float
    regime_max_rpm: float

class VerticalGeometry(StrictBaseModel):
    wheel_radius_m: float
    gear_z_m: float
    cg_z_m: float
    fuselage_bottom_z_m: float
    prop_hub_z_m: float
    prop_tip_z_m: float
    prop_clearance_ok: bool

class VisualGeometry(StrictBaseModel):
    fuselage_length_m: float
    fuselage_width_m: float
    fuselage_height_m: float
    wing_root_le_x_m: float
    wing_z_m: float
    htail_arm_x_m: float
    htail_span_m: float
    htail_chord_root_m: float
    htail_chord_tip_m: float
    htail_z_m: float
    wheel_width_m: Optional[float] = None

class GroundReactions(StrictBaseModel):
    charge_roue_nez_n: float
    charge_roue_gauche_n: float
    charge_roue_droite_n: float
    empattement_m: float
    voie_m: float
    cg_dans_polygone: bool
    wheel_radius_m: float
    
    # Validation metrics
    charge_nez_pct_calculee: float
    angle_tipback_deg_calcule: float
    garde_sol_helice_m_calculee: float
    garde_sol_fuselage_m_calculee: float

    # Detailed geometry (absolute coordinates)
    nose_gear_pos: List[float] # [x, y, z]
    main_gear_left_pos: List[float] # [x, y, z]
    main_gear_right_pos: List[float] # [x, y, z]
    
    # Spring and Damping
    k_nez_npm: float # Spring constant, N/m
    c_nez_nspm: float # Damping coefficient, N/m/s
    k_main_npm: float
    c_main_nspm: float
    
    # Friction
    static_friction: float
    dynamic_friction: float
    rolling_friction: float
    
    # Solver Diagnostics
    solver_d_min_m: float = 0.0
    solver_d_max_m: float = 0.0
    solver_cost: float = 0.0

    # Structural contact points
    structural_points: List[Dict[str, List[float]]] = Field(default_factory=list)

class ControlSurface(StrictBaseModel):
    name: str
    input_property: str
    output_property: str
    max_deflection_rad: float
    sign: float = 1.0

class ControlSystemDesign(StrictBaseModel):
    surfaces: List[ControlSurface]
    exported_properties: List[str]


class DerivedDesign(BaseModel):
    """
    This is the central data object for the design process.
    It's progressively populated by the calculator modules.
    Finally, it's used by the exporters to generate outputs.
    """
    # Calculation block outputs
    mass_budget: Optional[MassBudget] = None
    wing_geometry: Optional[WingGeometry] = None
    stability: Optional[Stability] = None
    empennages: Optional[Empennages] = None
    gouvernes: Optional[Gouvernes] = None
    fuselage: Optional[FuselageGeometry] = None
    power_and_battery: Optional[PowerAndBattery] = None
    ground_reactions: Optional[GroundReactions] = None
    control_system: Optional[ControlSystemDesign] = None
    vertical_geometry: Optional[VerticalGeometry] = None
    visual_geometry: Optional[VisualGeometry] = None

    # List of all detected issues
    blocking_issues: List[BlockingIssue] = Field(default_factory=list)

    model_config = ConfigDict(extra='allow')
