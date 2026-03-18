# Architecture cible

Observation : l'ancien projet mélangeait entrée, calcul, export et contrats dans le même dépôt.

## Découpage retenu
- `external/drone_spec` : vérité normative ;
- `src/uav_generator` : implémentation courante ;
- `tests/integration` : comportement interne ;
- `tests/e2e` : confrontation à la spécification ;
- `legacy_scripts/` : conservation des outils historiques.

## Règle d'écoulement
`project.yaml` → calculs → `DerivedDesign` → exporteurs → comparaison aux références du spec.

## Point de vigilance
Le champ `visual_geometry` existe déjà dans l'implémentation historique ; il manquait dans au moins un contrat d'inventaire. C'est typiquement le genre de divergence à neutraliser par séparation dépôt/specification.
