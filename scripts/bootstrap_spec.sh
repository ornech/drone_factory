#!/usr/bin/env bash
set -eu

SPEC_DIR="${1:-external/drone_spec}"

mkdir -p external
if [ ! -e "$SPEC_DIR" ]; then
  echo "Copier ou cloner drone_spec dans $SPEC_DIR" >&2
  exit 1
fi

bash scripts/readonly_spec.sh "$SPEC_DIR"
echo "Bootstrap terminé."
