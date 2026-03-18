#!/usr/bin/env bash
set -eu

SPEC_DIR="${1:-external/drone_spec}"

if [ ! -d "$SPEC_DIR" ]; then
  echo "ERREUR: dossier spec introuvable: $SPEC_DIR" >&2
  exit 1
fi

chmod -R a-w "$SPEC_DIR"
echo "Spec passée en lecture seule: $SPEC_DIR"
