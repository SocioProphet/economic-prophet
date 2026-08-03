# Deterministic, stdlib-only CI for the governed contracts in this repo.
# No third-party dependencies are required to run `make ladder`.

PYTHON ?= python3
PYTHONPATH := src

.PHONY: help ladder ladder-receipt test check

help:
	@echo "Targets:"
	@echo "  make ladder          # check the Jacob's Ladder of Assets contract (ALC-1)"
	@echo "  make ladder-receipt  # write build/asset_class_ladder_receipt.json"
	@echo "  make test            # run the test suite (needs pytest)"
	@echo "  make check           # ladder + test"

# ALC-1: schema-validate the canonical ladder, then apply every tooth. Pure
# stdlib -- this is the gate that cannot be skipped for lack of dependencies.
ladder:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m open_ep_framework.asset_ladder \
		--ladder examples/asset_class_ladder.json \
		--schema schemas/asset_class_ladder.schema.json

ladder-receipt:
	@mkdir -p build
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m open_ep_framework.asset_ladder \
		--ladder examples/asset_class_ladder.json \
		--schema schemas/asset_class_ladder.schema.json \
		--receipt build/asset_class_ladder_receipt.json

test:
	$(PYTHON) -m pytest -q

check: ladder test
