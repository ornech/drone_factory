# Politique de workspace agent

Commande d'installation de la lecture seule :

```bash
bash scripts/readonly_spec.sh external/drone_spec
```

## Ce que l'agent peut modifier
- `src/`
- `tests/integration/`
- `tests/e2e/`
- `docs/` du dépôt applicatif
- scripts locaux

## Ce que l'agent ne doit pas modifier
- `external/drone_spec/`
- les tags de version de la spec
- les références exportées de la spec
- le schéma d'entrée sans migration formelle

## Contournements à surveiller
- skip ou xfail ajoutés sur les E2E ;
- modification du `Makefile` pour éviter `tests/e2e` ;
- comparaison assouplie dans les assertions ;
- double logique cachée dans l'export AC3D.
