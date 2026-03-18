# uav_generator/exporters/jsbsim_writer.py
import math
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from . import ac3d_writer
from ..data_models import ProjectInput, DerivedDesign

# --- Constants for Conversion ---
KG_TO_SLUG = 0.0685218
M2_TO_FT2 = 10.7639
M_TO_FT = 3.28084
NSPM_TO_LBSFTSEC = 0.0685218 # N*s/m to lbf*s/ft
NPM_TO_LBSFT = 0.0685218 # N/m to lbf/ft

def _prepare_context(project: ProjectInput, design: DerivedDesign) -> dict:
    """
    Prepares a flattened dictionary with all necessary data for the Jinja2 templates.
    This includes coordinate transformations and inertia calculations.
    """
    # --- 1. Coordinate Systems ---
    # Design Frame (from ground.py): X-back, Y-right, Z-up, origin at nose [0,0,0]
    # JSBSim structural frame is identical.
    # Transformation: jsb_x = design_x, jsb_y = design_y, jsb_z = design_z
    
    # --- 2. Extract Key Data ---
    gr = design.ground_reactions
    wg = design.wing_geometry
    sb = design.stability
    mb = design.mass_budget
    pb = design.power_and_battery
    
    # Absolute CG position in the design frame, calculated in ground.py
    cg_x, cg_y, cg_z = design.stability.cg_location_m

    # --- 3. Total Inertia Tensor Calculation (Approximation) ---
    # This calculates the inertia for the entire aircraft (MTOW) about its center of gravity.
    # JSBSim expects the inertia tensor to be specified about the CG.
    
    # Part 1: Empty airframe inertia (approximated as simple shapes)
    Ixx_wing = (1/12) * (mb.masse_vide_kg * 0.6) * (wg.envergure_m**2) # 60% of empty mass is wing
    Iyy_wing = (1/12) * (mb.masse_vide_kg * 0.6) * (wg.corde_racine_m**2) # Simplified
    fuselage_mass = mb.masse_vide_kg * 0.4
    fuselage_length = wg.envergure_m * 0.6 # Heuristic
    Iyy_fuse = (1/12) * fuselage_mass * (fuselage_length**2)
    # Perpendicular axis theorem for cruciform shape (Izz = Ixx_wing + Iyy_fuse)
    Izz_airframe = Ixx_wing + Iyy_fuse
    Iyy_airframe = Iyy_wing + Iyy_fuse
    Ixx_airframe = Ixx_wing
    
    # Part 2: Inertia of point masses (payload, battery) about the CG
    # Using Parallel Axis Theorem: I = I_local + m*d^2. For point masses, I_local = 0.
    # Assume payload is at the CG, so its inertia contribution is 0.
    # Assume battery is 0.1m forward of CG.
    batt_dist_from_cg = 0.1
    iyy_batt_kg_m2 = mb.masse_batterie_kg * (batt_dist_from_cg**2)
    izz_batt_kg_m2 = mb.masse_batterie_kg * (batt_dist_from_cg**2)

    # Part 3: Total inertia about the aircraft's CG
    total_ixx_kg_m2 = Ixx_airframe
    total_iyy_kg_m2 = Iyy_airframe + iyy_batt_kg_m2
    total_izz_kg_m2 = Izz_airframe + izz_batt_kg_m2

    # Part 4: Convert to imperial units for JSBSim
    ixx_slug_ft2 = total_ixx_kg_m2 * KG_TO_SLUG * (M_TO_FT**2)
    iyy_slug_ft2 = total_iyy_kg_m2 * KG_TO_SLUG * (M_TO_FT**2)
    izz_slug_ft2 = total_izz_kg_m2 * KG_TO_SLUG * (M_TO_FT**2)

    # --- 4. Flattened Context for Jinja2 ---
    context = {
        "project": project,
        "design": design,

        "uav_name": project.projet.nom,
        "description": project.projet.description,
        "creation_date": datetime.now().strftime("%Y-%m-%d"),
        "jsbsim_file_path": f"JSBSim/{project.projet.nom}.xml",
        "model_xml_filename": f"{project.projet.nom}-model.xml",
        "fdm_type": "JSBSim",
        
        # --- Feature Flags for Minimal Viable Package ---
        "enable_sound": False, # Disable until a valid sound.xml is generated
        "enable_electrical_system": False, # Disable until electrics.xml is validated

        # Metrics
        "wing_area_m2": wg.surface_alaire_m2,
        "wing_span_m": wg.envergure_m,
        "wing_chord_m": wg.mac_m,
        "wing_area_sqft": wg.surface_alaire_m2 * M2_TO_FT2,
        "wing_span_ft": wg.envergure_m * M_TO_FT,
        "wing_chord_ft": wg.mac_m * M_TO_FT,
        "htail_area_m2": design.empennages.surface_h_m2,
        "htail_arm_m": 3.0 * wg.mac_m, # Same heuristic as in aero.py
        "vtail_area_m2": design.empennages.surface_v_m2,
        "vtail_arm_m": 3.0 * wg.mac_m,
        
        # Mass Balance (using total weight and specified CG)
        "ixx_slug_ft2": ixx_slug_ft2,
        "iyy_slug_ft2": iyy_slug_ft2,
        "izz_slug_ft2": izz_slug_ft2,

        # Point Masses (for the <pointmass> approach in the template)
        # All locations are in JSBSim structural frame (X-back, Y-right, Z-up)
        "empty_weight_kg": mb.masse_vide_kg,
        "payload_mass_kg": mb.masse_charge_utile_kg,
        "battery_mass_kg": mb.masse_batterie_kg,
        # Payload and empty weight are placed to achieve the target CG
        "payload_location_m": [cg_x, cg_y, cg_z],
        # Battery is placed 0.1m forward of the CG (towards nose, so -0.1 in X)
        "battery_location_m": [cg_x - 0.1, cg_y, cg_z],

        # Visual Reference Point (VRP) is the center of the 3D model, which we
        # align with the aircraft's Center of Gravity.
        "vrp_location_m": [cg_x, cg_y, cg_z],

        # Aerodynamic reference point (AERORP) is the structural frame origin, at the nose.
        "aerorp_x_m": 0.0,
        "aerorp_y_m": 0.0,
        "aerorp_z_m": 0.0,

        # Ground Reactions
        "main_gear_left_pos_m": [gr.main_gear_left_pos[0], gr.main_gear_left_pos[1], gr.main_gear_left_pos[2]],
        "main_gear_right_pos_m": [gr.main_gear_right_pos[0], gr.main_gear_right_pos[1], gr.main_gear_right_pos[2]],
        "nose_gear_pos_m": [gr.nose_gear_pos[0], gr.nose_gear_pos[1], gr.nose_gear_pos[2]],
        "k_main_npm": gr.k_main_npm,
        "k_main_lbsft": gr.k_main_npm * NPM_TO_LBSFT,
        "c_main_nspm": gr.c_main_nspm,
        "c_main_lbsftsec": gr.c_main_nspm * NSPM_TO_LBSFTSEC,
        "k_nez_npm": gr.k_nez_npm,
        "k_nez_lbsft": gr.k_nez_npm * NPM_TO_LBSFT,
        "c_nez_nspm": gr.c_nez_nspm,
        "c_nez_lbsftsec": gr.c_nez_nspm * NSPM_TO_LBSFTSEC,
        "static_friction": gr.static_friction,
        "dynamic_friction": gr.dynamic_friction,
        "rolling_friction": gr.rolling_friction,
        "structural_points": [{"name": list(p.keys())[0], "pos": [list(p.values())[0][0], list(p.values())[0][1], list(p.values())[0][2]]} for p in gr.structural_points],

        # Propulsion
        "propeller_diam_in": project.helice.diametre_in,
        "propeller_pitch_in": project.helice.pas_in,
        "propeller_num_blades": project.helice.nb_pales,
        "max_power_w": project.propulsion.puissance_max_w,
        "max_rpm": pb.regime_max_rpm,
        "kv_moteur": project.propulsion.kv_moteur,
        "tension_batterie_v": project.propulsion.tension_batterie_v,
        "capacite_batterie_ah": design.power_and_battery.capacite_batterie_ah
    }
    return context

def generate_jsbsim_package(project: ProjectInput, design: DerivedDesign, output_dir: Path):
    """
    Generates the full JSBSim aircraft package from templates.
    Validates FCS-aero contract before rendering.
    """
    from ..calculators.control_system import validate_fcs_contract
    design = validate_fcs_contract(design)
    if design.blocking_issues:
        print("FATAL: FCS-Aero contract validation failed.")
        for issue in design.blocking_issues:
            print(f"  - {issue.code}: {issue.cause}")
        return False
    
    template_dir = Path(__file__).parent.parent / 'templates'
    env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)

    uav_name = project.projet.nom
    
    print(f"INFO: Generating FlightGear package in {output_dir}...")

    try:
        template_context = _prepare_context(project, design)
    except Exception as e:
        print(f"FATAL: Failed to prepare template context. Error: {e}")
        (output_dir / "GENERATION_FAILED.txt").write_text(f"Context preparation failed: {e}")
        return False

    def render_template(template_name, output_path):
        try:
            template = env.get_template(template_name)
            rendered_content = template.render(template_context)
            with open(output_path, 'w') as f:
                f.write(rendered_content)
            print(f"  - Wrote {output_path}")
        except Exception as e:
            print(f"ERROR: Failed to generate {output_path.name}. {e}")
            (output_dir / "GENERATION_FAILED.txt").write_text(f"Template rendering failed for {template_name}: {e}")
            raise

    try:
        # FDM files should be in a dedicated JSBSim subdirectory for clarity and standard compliance.
        jsbsim_dir = output_dir / "JSBSim"
        jsbsim_dir.mkdir(exist_ok=True)
        render_template('aircraft.xml.j2', jsbsim_dir / f"{uav_name}.xml")

        # Engine and propeller files go into the Engines subdirectory
        engines_dir = output_dir / "Engines"
        engines_dir.mkdir(exist_ok=True)
        render_template('engine_electric.xml.j2', engines_dir / 'engine_electric.xml')
        render_template('propeller.xml.j2', engines_dir / 'propeller.xml')

        # Systems files
        systems_dir = output_dir / "Systems"
        systems_dir.mkdir(exist_ok=True)
        
        # CORRECTION 4: Only generate electrics.xml if the feature flag is true
        if template_context.get("enable_electrical_system"):
            render_template('electrics.xml.j2', systems_dir / 'electrics.xml')
        render_template('flight-control.xml.j2', systems_dir / 'flight-control.xml')

        # Models files
        models_dir = output_dir / "Models"
        models_dir.mkdir(exist_ok=True)
        render_template('model.xml.j2', models_dir / f"{uav_name}-model.xml")
        ac3d_writer.generate_ac3d_model(project, design, models_dir / f"{uav_name}.ac")

        # Root file
        render_template('set.xml.j2', output_dir / f"{uav_name}-set.xml")

        # Docs
        docs_dir = output_dir / "Docs"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "README.md").write_text(f"# {uav_name}\n\nGenerated by UAV-Generator.")

        # Nasal
        nasal_dir = output_dir / "Nasal"
        nasal_dir.mkdir(exist_ok=True)
        (nasal_dir / "init.nas").touch()

    except Exception:
        return False

    return True
