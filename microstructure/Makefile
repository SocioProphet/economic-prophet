PYTHON ?= python3

.PHONY: validate validate-compile validate-order-flow-process

# Aggregate target for the microstructure contract module.
validate: validate-compile validate-order-flow-process

# Byte-compile the deterministic, stdlib-only estimator + validator.
validate-compile:
	$(PYTHON) -m py_compile scripts/order_flow_estimators.py scripts/validate_order_flow_process.py

# OrderFlowProcess + TrendSignal contracts: VERIFIES + REJECTS + COHERENCE + receipt teeth.
validate-order-flow-process:
	$(PYTHON) scripts/validate_order_flow_process.py
