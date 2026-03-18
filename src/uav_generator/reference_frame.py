"""
Repère de vérité unique du projet.

Convention retenue :
- origine : nez de l'appareil
- axe X : vers l'arrière
- axe Y : vers la droite
- axe Z : vers le haut

Toutes les positions physiques critiques doivent être exprimées dans ce repère :
- CG
- trains
- points structurels
- géométrie de base exportée vers JSBSim et AC3D
"""

REFERENCE_FRAME_NAME = "NOSE_X_AFT_Y_RIGHT_Z_UP"


def frame_metadata() -> dict:
    return {
        "name": REFERENCE_FRAME_NAME,
        "origin": "nose",
        "x_axis": "aft",
        "y_axis": "right",
        "z_axis": "up",
    }
