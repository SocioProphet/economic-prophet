# Deterministic, stdlib-only CI for the governed contracts in this repo.
# No third-party dependencies are required to run `make ladder`.

PYTHON ?= python3
PYTHONPATH := src

.PHONY: help ladder ladder-receipt outcome-pricing outcome-pricing-receipt welfare-annealing benchmarking value-ordering value-relativity test check

help:
	@echo "Targets:"
	@echo "  make ladder                   # check the Jacob's Ladder of Assets contract (ALC-1)"
	@echo "  make ladder-receipt           # write build/asset_class_ladder_receipt.json"
	@echo "  make outcome-pricing          # price the OPX-1 engagement fixture (stdlib gate)"
	@echo "  make outcome-pricing-receipt  # write build/outcome_pricing_receipt.json"
	@echo "  make welfare-annealing        # run the WEA-1 Welfare-Annealing contract teeth"
	@echo "  make benchmarking             # check the index-relative benchmarking contract (IRB-1)"
	@echo "  make value-ordering           # check the relativity-of-price value-ordering contract (RVO-1)"
	@echo "  make value-relativity         # IRB-1 + RVO-1 fixture teeth (needs jsonschema)"
	@echo "  make test                     # run the test suite (needs pytest)"
	@echo "  make check                    # ladder + outcome-pricing + welfare-annealing + benchmarking + value-ordering + test"

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

# WEA-1: run the Welfare-Annealing contract teeth (VERIFIES + REJECTS + COHERENCE).
# Needs jsonschema (the Draft 2020-12 validator); the module itself is pure stdlib.
welfare-annealing:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/validate_welfare_annealing.py

# IRB-1: index-relative benchmarking -- baseline+idiosyncratic decomposition with
# the cross-frame dimensionless-differential teeth.
benchmarking:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m open_ep_framework.benchmarking \
		--book examples/benchmarking/index_relative_book.valid.json \
		--schema schemas/index_relative_cohort.schema.json

# RVO-1: relativity of price -- CRDT order-independent merge + no-global-price teeth.
value-ordering:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m open_ep_framework.value_ordering \
		--record examples/value_ordering/eventual_consistency.valid.json \
		--schema schemas/value_frame_observation.schema.json

# Full fixture-driven teeth for both contracts (VERIFIES + REJECTS + COHERENCE).
value-relativity:
	$(PYTHON) scripts/validate_benchmarking.py
	$(PYTHON) scripts/validate_value_ordering.py

test:
	$(PYTHON) -m pytest -q

check: ladder outcome-pricing welfare-annealing benchmarking value-ordering test
