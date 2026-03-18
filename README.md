# drone_factory

Commande de contrôle :

```bash
pytest -q
```

Ce dépôt contient l'implémentation modifiable.  
La vérité normative n'est pas ici. Elle est consommée via `external/drone_spec`.

## Principes
- pas de formule normative recopiée sans référence ;
- pas de snapshot local utilisé comme vérité ;
- pas de modification de `external/drone_spec` depuis l'environnement agent ;
- toute divergence doit être visible dans les tests E2E.

## État après migration
Le code historique a été conservé dans `src/uav_generator/`.  
Les anciens scripts ont été archivés dans `legacy_scripts/`.  
Les anciens tests de contrat ont été déplacés dans `docs/legacy_contract_tests_snapshot/` pour éviter qu'ils ne restent la vérité implicite du nouveau dépôt.
