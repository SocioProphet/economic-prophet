# Deterministic, stdlib-only CI for the governed contracts in this repo.
# No third-party dependencies are required to run `make ladder`.

PYTHON ?= python3
PYTHONPATH := src

.PHONY: help ladder ladder-receipt outcome-pricing outcome-pricing-receipt test check

help:
	@echo "Targets:"
	@echo "  make ladder                   # check the Jacob's Ladder of Assets contract (ALC-1)"
	@echo "  make ladder-receipt           # write build/asset_class_ladder_receipt.json"
	@echo "  make outcome-pricing          # price the OPX-1 engagement fixture (stdlib gate)"
	@echo "  make outcome-pricing-receipt  # write build/outcome_pricing_receipt.json"
	@echo "  make test                     # run the test suite (needs pytest)"
	@echo "  make check                    # ladder + outcome-pricing + test"

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

# OPX-1: price the canonical engagement fixture end-to-end (V / VoI / RAROC /
# discount / equilibrium / mesh-split), enforcing every tooth. Pure stdlib.
outcome-pricing:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m open_ep_framework.outcome_pricing \
		--engagement examples/outcome_pricing_engagement.json \
		--schema schemas/outcome_pricing.schema.json

outcome-pricing-receipt:
	@mkdir -p build
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m open_ep_framework.outcome_pricing \
		--engagement examples/outcome_pricing_engagement.json \
		--schema schemas/outcome_pricing.schema.json \
		--receipt build/outcome_pricing_receipt.json

test:
	$(PYTHON) -m pytest -q

check: ladder outcome-pricing test
