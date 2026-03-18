SPEC_DIR ?= external/drone_spec

.PHONY: test spec-check readonly-spec
test:
	pytest -q

spec-check:
	PYTHONPATH=src pytest -q tests/e2e

readonly-spec:
	bash scripts/readonly_spec.sh $(SPEC_DIR)
