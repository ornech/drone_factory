# Notes de migration

## Éléments déplacés
- `schemas/` → `drone_spec/schemas/`
- `examples/` → `drone_spec/fixtures/`
- `build/generated_output/` → `drone_spec/references/`
- `tests/contracts/` → `drone_spec/legacy_contracts/`

## Éléments conservés côté application
- `src/uav_generator/`
- `scripts/` archivés dans `legacy_scripts/`

## Dette encore présente
Le code historique garde des formules et des règles documentées en parallèle.  
La migration sépare les responsabilités, mais ne prouve pas encore que chaque formule a une source unique.
