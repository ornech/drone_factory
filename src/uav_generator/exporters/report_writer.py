# uav_generator/exporters/report_writer.py
import yaml
import json
from pathlib import Path
from ..data_models import ProjectInput, DerivedDesign

def generate_reports(project: ProjectInput, design: DerivedDesign, output_dir: Path):
    """
    Generates all human-readable and data-centric report files.
    - `construction_sheet.yaml`: Simplified data for real-world building.
    - `derived_design.json`: A complete dump of the calculated design parameters.
    - `validation_report.txt`: A summary of issues found.
    """
    reports_dir = output_dir / "Reports"
    reports_dir.mkdir(exist_ok=True)
    
    print(f"INFO: Generating reports in {reports_dir}...")
    
    # 1. Generate construction_sheet.yaml
    try:
        # Check if all required data is present
        if not all([design.wing_geometry, design.stability, design.mass_budget, design.empennages, design.gouvernes, design.power_and_battery]):
             print("ERROR: Missing calculated data, cannot generate construction sheet.")
             return False

        cg_from_le_m = design.stability.cg_cible_pct_mac * design.wing_geometry.mac_m
        
        construction_sheet_data = {
            "nom_projet": project.projet.nom,
            "geometrie_principale": {
                "envergure_m": round(design.wing_geometry.envergure_m, 3),
                "corde_racine_m": round(design.wing_geometry.corde_racine_m, 3),
                "corde_saumon_m": round(design.wing_geometry.corde_saumon_m, 3),
                "surface_alaire_m2": round(design.wing_geometry.surface_alaire_m2, 3),
            },
            "centrage": {
                "cg_depuis_bord_attaque_mac_m": round(cg_from_le_m, 4),
                "marge_statique_pct": design.stability.marge_statique_pct * 100,
            },
            "masses": {
                "masse_totale_au_decollage_kg": round(design.mass_budget.mtow_kg, 2),
                "masse_a_vide_estimee_kg": round(design.mass_budget.masse_vide_kg, 2),
                "masse_batterie_estimee_kg": round(design.mass_budget.masse_batterie_kg, 2),
                "charge_utile_kg": design.mass_budget.masse_charge_utile_kg,
            },
            "empennages": {
                "surface_horizontale_m2": round(design.empennages.surface_h_m2, 3),
                "surface_verticale_m2": round(design.empennages.surface_v_m2, 3),
            },
            "gouvernes": {
                "surface_ailerons_m2": round(design.gouvernes.surface_ailerons_m2, 3),
                "surface_profondeur_m2": round(design.gouvernes.surface_profondeur_m2, 3),
                "surface_derive_m2": round(design.gouvernes.surface_derive_m2, 3),
            },
            "profils_recommandes": {
                "aile_racine": design.wing_geometry.profil_racine,
                "aile_saumon": design.wing_geometry.profil_saumon,
                # Empennage profiles could be added here as well
            },
            "motorisation_recommandee": {
                "puissance_continue_w": project.propulsion.puissance_continue_w,
                "puissance_max_w": project.propulsion.puissance_max_w,
                "kv_moteur": project.propulsion.kv_moteur,
                "tension_batterie_v": project.propulsion.tension_batterie_v,
            },
            "batterie_recommandee": {
                "capacite_ah": round(design.power_and_battery.capacite_batterie_ah, 2),
                "tension_v": project.propulsion.tension_batterie_v,
            },
            "helice_recommandee": {
                "diametre_in": project.helice.diametre_in,
                "pas_in": project.helice.pas_in,
                "nb_pales": project.helice.nb_pales,
            }
        }

        sheet_path = reports_dir / "construction_sheet.yaml"
        with open(sheet_path, 'w') as f:
            yaml.dump(construction_sheet_data, f, default_flow_style=False, sort_keys=False)
        print(f"  - Wrote {sheet_path}")

    except AttributeError as e:
        print(f"ERROR: Failed to generate construction sheet due to missing data: {e}")
        return False
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while generating construction sheet: {e}")
        return False

    # 2. Generate derived_design.json
    try:
        json_path = reports_dir / "derived_design.json"
        with open(json_path, 'w') as f:
            # Pydantic's model_dump_json is perfect for this
            f.write(design.model_dump_json(indent=2))
        print(f"  - Wrote {json_path}")
    except Exception as e:
        print(f"ERROR: Failed to generate derived_design.json. {e}")
        return False

    # 3. Generate validation_report.txt
    try:
        report_path = reports_dir / "validation_report.txt"
        with open(report_path, 'w') as f:
            f.write("="*60 + "\n")
            f.write("         UAV Generation Validation Report\n")
            f.write("="*60 + "\n\n")
            
            if not design.blocking_issues:
                f.write("STATUS: SUCCESS\n\n")
                f.write("All automated checks passed. The design is considered valid based on the available heuristics.\n")
            else:
                f.write(f"STATUS: FAILED - {len(design.blocking_issues)} BLOCKING ISSUE(S) FOUND\n\n")
                f.write("The following issues must be addressed:\n\n")
                for i, issue in enumerate(design.blocking_issues, 1):
                    f.write(f"--- Issue {i}: {issue.code} ---\n")
                    f.write(f"  Cause: {issue.cause}\n")
                    f.write( "  Proposals:\n")
                    for prop in issue.proposals:
                        f.write(f"    - {prop.description}\n")
                    f.write("\n")
        print(f"  - Wrote {report_path}")
    
    except Exception as e:
        print(f"ERROR: Failed to generate validation_report.txt. {e}")
        return False
        
    return True
