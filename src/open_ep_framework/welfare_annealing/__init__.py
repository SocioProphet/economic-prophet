"""Value-Energy-Conservation Welfare-Annealing (WEA-1): the estate's "better framework".

The constructive, normative INVERSE of "Silent Weapons for Quiet Wars": it keeps the same
value-as-energy physics -- value-energy is conserved in exchange, growth is a production
source term, and allocations flow under a free-energy potential read with a laminar/turbulent
lens -- but FLIPS the objective from elite-control/extraction to a global welfare (QoL) index.

Four constituent contracts-with-teeth, each consuming an existing estate contract BY REFERENCE
(consume-not-fork), assembled into one welfare-annealing framework:

  * ``qol``      -- the HDI-generalized global QoL welfare functional (population x life-length
                    x health x education) the anneal descends toward; the required-dimension tooth.
  * ``energy``   -- value-energy conservation in exchange (reuses IC-1 ``settlement``, #39) and
                    the carrying-capacity discount + renewable source term with the false-growth
                    flag (reuses ALC-1 ``asset_ladder`` renewability, #52).
  * ``anneal``   -- the gradient-flow annealing state machine over allocations, classified
                    laminar vs turbulent with the FRL-1 turbulence lens (reuses ``flow_regime``
                    Lyapunov/regime taxonomy, #54).
  * ``discount`` -- Fisher real rate (reuses ``inflation``), the Fisher-ideal index, MV=PQ, and
                    the social discount rate (Ramsey; Stern vs Nordhaus) as the MASTER parameter
                    with a reconciling sensitivity sweep.
  * ``gaia_binding`` -- emits the two GAIA value-flow manifests (value_flow_binding.v1 +
                    twin_scale_transfer.v1) that bind this spine UPWARD into the gaia-world-model
                    world model, enforcing the gaia teeth (T1-CONST/T4-REGEN/T3-QOL/T2-CONSERVE,
                    T1-RESERVE admit-with-flag) on real EP runs.
  * ``contract`` -- the WEA-1 orchestrator: runs a record, applies the teeth, emits a receipt.

Measurement / simulation / audit only. Deterministic and stdlib-only for hermetic CI.
"""
from . import anneal, contract, discount, energy, gaia_binding, qol  # noqa: F401
from .contract import CONTRACT, WelfareAnnealingError, emit_receipt, run_record
from .gaia_binding import GaiaBindingError, emit_manifests

__all__ = [
    "qol",
    "energy",
    "anneal",
    "discount",
    "gaia_binding",
    "contract",
    "CONTRACT",
    "WelfareAnnealingError",
    "GaiaBindingError",
    "run_record",
    "emit_receipt",
    "emit_manifests",
]
