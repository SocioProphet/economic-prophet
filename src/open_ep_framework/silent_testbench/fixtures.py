"""DOCUMENTED, CITED historical reference fixtures for the falsification pass.

CI is hermetic (no network), so the empirical confrontation is run against reference
figures transcribed here from the published literature, with the source stated beside each
number. These are ORDERS OF MAGNITUDE and headline published estimates -- enough to test
the doc's SPECIFIC claims, not a substitute for a live data feed (a follow-up issue tracks
wiring EIA / BLS / IMF / Reinhart-Rogoff series as real sources; see the PR body).

Every figure is a matter of public record; nothing here is proprietary or personal.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# OIL / GASOLINE PRICE SHOCKS
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OilShock:
    year: int
    label: str
    crude_before_usd_bbl: float
    crude_after_usd_bbl: float
    retail_gasoline_before_usd_gal: float
    retail_gasoline_after_usd_gal: float
    source: str

    @property
    def crude_pct_change(self) -> float:
        return (self.crude_after_usd_bbl - self.crude_before_usd_bbl) / self.crude_before_usd_bbl

    @property
    def gasoline_pct_change(self) -> float:
        return ((self.retail_gasoline_after_usd_gal - self.retail_gasoline_before_usd_gal)
                / self.retail_gasoline_before_usd_gal)


# Figures: U.S. EIA historical crude/retail-gasoline series; BLS CPI motor-fuel.
OIL_SHOCKS = (
    OilShock(
        year=1973, label="OPEC embargo (Oct 1973-Mar 1974)",
        crude_before_usd_bbl=3.0, crude_after_usd_bbl=11.65,        # posted Arabian Light
        retail_gasoline_before_usd_gal=0.39, retail_gasoline_after_usd_gal=0.53,
        source="EIA crude oil posted prices; BLS CPI motor fuel 1973-74 (~+300% crude, "
               "~+36% U.S. retail gasoline).",
    ),
    OilShock(
        year=1979, label="Iranian Revolution / second oil shock (1979-1981)",
        crude_before_usd_bbl=14.0, crude_after_usd_bbl=35.0,
        retail_gasoline_before_usd_gal=0.86, retail_gasoline_after_usd_gal=1.31,
        source="EIA refiner acquisition cost of crude; EIA U.S. all-grades retail gasoline "
               "1979->1981 (crude ~2.5x, retail gasoline ~+52%).",
    ),
    OilShock(
        year=2008, label="2008 commodity spike (peak Jul 2008)",
        crude_before_usd_bbl=72.0, crude_after_usd_bbl=147.27,       # WTI intraday peak
        retail_gasoline_before_usd_gal=3.05, retail_gasoline_after_usd_gal=4.11,
        source="EIA WTI spot (peak $147.27, 2008-07-11); EIA U.S. regular retail gasoline "
               "monthly avg peak $4.11/gal, Jul 2008.",
    ),
)


@dataclass(frozen=True)
class ElasticityEstimate:
    label: str
    value: float                    # point estimate (negative = normal good)
    low: float
    high: float
    horizon: str                    # "short_run" | "long_run"
    era: str
    source: str


# Published gasoline-demand price elasticities. The short-run own-price elasticity is small
# and negative; it FELL in magnitude after 2000. These are the numbers the shock test must
# reproduce (because the shock test IS elasticity estimation).
GASOLINE_ELASTICITIES = (
    ElasticityEstimate(
        label="US short-run own-price, 1975-1980", value=-0.27, low=-0.34, high=-0.21,
        horizon="short_run", era="1975-1980",
        source="Hughes, Knittel & Sperling (2008), 'Evidence of a Shift in the Short-Run "
               "Price Elasticity of Gasoline Demand', The Energy Journal 29(1).",
    ),
    ElasticityEstimate(
        label="US short-run own-price, 2001-2006", value=-0.055, low=-0.077, high=-0.034,
        horizon="short_run", era="2001-2006",
        source="Hughes, Knittel & Sperling (2008), The Energy Journal 29(1) -- short-run "
               "elasticity fell to -0.034..-0.077.",
    ),
    ElasticityEstimate(
        label="Meta-analytic short-run mean", value=-0.26, low=-0.34, high=-0.20,
        horizon="short_run", era="meta",
        source="Espey (1998) meta-analysis, Energy Economics; Brons et al. (2008), "
               "'A meta-analysis of the price elasticity of gasoline demand', Energy Economics.",
    ),
    ElasticityEstimate(
        label="Meta-analytic long-run mean", value=-0.58, low=-0.84, high=-0.31,
        horizon="long_run", era="meta",
        source="Espey (1998); Brons et al. (2008) long-run ~ -0.84; Dahl (2012), Energy Policy.",
    ),
)


# --------------------------------------------------------------------------- #
# DEBT / GDP CRISES (Reinhart-Rogoff and the HAP correction) + RESOLUTION MODES
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DebtCrisis:
    episode: str
    year: int
    peak_debt_gdp: float            # gross public debt / GDP at/around the episode
    resolution_mode: str            # default | restructuring | inflation | growth | financial_repression
    population_negation: bool       # did the episode resolve via genocide/depopulation?
    source: str


# The teeth of Phase 2's STRONG-FORM falsification: high-debt crises resolve through
# financial mechanisms -- default, restructuring, inflation, growth/surplus -- and in NO
# case through population-negation. ``population_negation`` is False for every episode.
DEBT_CRISES = (
    DebtCrisis(
        episode="UK post-Napoleonic wars", year=1815, peak_debt_gdp=2.0,
        resolution_mode="growth", population_negation=False,
        source="Reinhart & Rogoff (2009), 'This Time is Different'; UK debt/GDP ~200% in "
               "1815-1822, worked down over a century via growth and primary surpluses.",
    ),
    DebtCrisis(
        episode="Weimar Germany hyperinflation", year=1923, peak_debt_gdp=1.5,
        resolution_mode="inflation", population_negation=False,
        source="Reinhart & Rogoff (2009); domestic war debt inflated away 1921-1923, then "
               "currency reform (Rentenmark).",
    ),
    DebtCrisis(
        episode="US post-WWII", year=1946, peak_debt_gdp=1.06,
        resolution_mode="financial_repression", population_negation=False,
        source="US Treasury/OMB historical tables; gross federal debt ~106% of GDP in 1946, "
               "reduced via growth and mild inflation ('financial repression').",
    ),
    DebtCrisis(
        episode="Latin American debt crisis (Mexico)", year=1982, peak_debt_gdp=0.53,
        resolution_mode="restructuring", population_negation=False,
        source="Reinhart & Rogoff (2009); Mexico Aug-1982 moratorium, resolved via Brady "
               "Plan restructuring (1989-1990).",
    ),
    DebtCrisis(
        episode="Russia 1998 default", year=1998, peak_debt_gdp=0.68,
        resolution_mode="default", population_negation=False,
        source="Reinhart & Rogoff (2009); Aug-1998 GKO domestic-debt default + rouble "
               "devaluation.",
    ),
    DebtCrisis(
        episode="Argentina 2001 default", year=2001, peak_debt_gdp=0.62,
        resolution_mode="default", population_negation=False,
        source="Reinhart & Rogoff (2009); Dec-2001 sovereign default (~$100bn), "
               "restructured 2005/2010.",
    ),
    DebtCrisis(
        episode="Greece / euro-area crisis", year=2012, peak_debt_gdp=1.72,
        resolution_mode="restructuring", population_negation=False,
        source="Eurostat; Greece PSI (Mar-2012), the largest sovereign-debt restructuring "
               "(~EUR100bn private-sector haircut).",
    ),
)


@dataclass(frozen=True)
class DebtGrowthThreshold:
    claim: str
    threshold_debt_gdp: float
    claimed_effect: str
    status: str
    source: str = ""
    corrections: tuple = field(default_factory=tuple)


# The famous "90% cliff" -- and its published refutation. Encoding the CORRECTION is the
# honest move: the weak form (high debt is associated with lower growth / more fragility)
# survives; the sharp causal cliff does NOT.
DEBT_GROWTH_THRESHOLD = DebtGrowthThreshold(
    claim="public debt above 90% of GDP sharply lowers median growth",
    threshold_debt_gdp=0.90,
    claimed_effect="median real GDP growth drops sharply (RR-2010 reported a fall to "
                   "roughly -0.1% above the 90% line)",
    status="weak_association_survives_sharp_cliff_refuted",
    source="Reinhart & Rogoff (2010), 'Growth in a Time of Debt', AER 100(2):573-578.",
    corrections=(
        "Herndon, Ash & Pollin (2013), 'Does High Public Debt Consistently Stifle Economic "
        "Growth? A Critique of Reinhart and Rogoff', Cambridge Journal of Economics -- found "
        "a spreadsheet coding error, selective country-year exclusions, and unconventional "
        "weighting; corrected, growth above 90% debt/GDP is ~2.2%, not -0.1%, and the sharp "
        "threshold disappears.",
    ),
)


# --------------------------------------------------------------------------- #
# THE DOC'S SPECIFIC BEHAVIOURAL CLAIM (SILENT): a gasoline-price shock propagates to
# aggregate public "reaction" -- the pamphlet literally lists headache, hostility, violence,
# and increased tavern attendance as measurable outputs of the price shock. We record it as
# a NON-VALIDATED assertion: no out-of-sample coefficient is offered by the document.
# --------------------------------------------------------------------------- #
DOC_BEHAVIORAL_CLAIM = {
    "source": "Silent Weapons for Quiet Wars, 'the shock front' / economic-inductance "
              "sections (a stable coefficient links a gasoline-price shock to public "
              "behavioural outputs incl. headaches, hostility, violence, tavern attendance).",
    "claimed_outputs": ["headache", "hostility", "violence", "tavern_attendance"],
    "offered_coefficient": None,          # the document offers no fitted, testable coefficient
    "offered_out_of_sample_test": False,  # and no out-of-sample validation
}
