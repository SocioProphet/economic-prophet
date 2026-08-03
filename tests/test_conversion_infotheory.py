"""Teeth for information-theoretic conversion attribution + martech economics."""
import math

from open_ep_framework.conversion_infotheory import (
    entropy, kl_divergence, mutual_information, information_gain_attribution,
    channel_diversity, cac, roas, ltv_cac_ratio, payback_months, marketing_efficiency,
    ChannelStats,
)


def test_entropy_bounds():
    assert abs(entropy([0.5, 0.5]) - 1.0) < 1e-9      # fair coin = 1 bit
    assert entropy([1.0, 0.0]) == 0.0                  # certainty = 0 bits
    assert entropy([0.25, 0.25, 0.25, 0.25]) == 2.0    # 4 equal = 2 bits


def test_kl_zero_iff_identical_and_nonneg():
    assert kl_divergence([0.5, 0.5], [0.5, 0.5]) == 0.0
    assert kl_divergence([0.6, 0.4], [0.5, 0.5]) > 0.0
    assert kl_divergence([0.9, 0.1], [0.5, 0.5]) > kl_divergence([0.6, 0.4], [0.5, 0.5])


def test_uninformative_channels_have_zero_mutual_information():
    # every channel converts at the SAME rate -> knowing the channel tells you nothing
    ch = {"a": ChannelStats(1000, 100), "b": ChannelStats(2000, 200), "c": ChannelStats(500, 50)}
    assert mutual_information(ch) < 1e-9


def test_predictive_channel_has_high_mutual_information():
    # one channel always converts, one never -> channel fully determines outcome
    ch = {"always": ChannelStats(500, 500), "never": ChannelStats(500, 0)}
    mi = mutual_information(ch)
    assert mi > 0.99   # ~ H(Y) with a 50/50 base rate = 1 bit


def test_attribution_shares_sum_to_one_and_bits_sum_to_mi():
    ch = {"paid": ChannelStats(1000, 40), "organic": ChannelStats(1000, 120), "social": ChannelStats(1000, 20)}
    out = information_gain_attribution(ch)
    shares = [v["share"] for v in out["channels"].values()]
    assert abs(sum(shares) - 1.0) < 1e-9
    info = sum(v["info_bits"] for v in out["channels"].values())
    assert abs(info - out["mutual_information_bits"]) < 1e-9
    assert abs(out["mutual_information_bits"] - mutual_information(ch)) < 1e-9


def test_more_divergent_channel_gets_more_credit_than_last_touch_would():
    # organic (3x base conversion) should out-attribute a high-volume average channel
    ch = {"organic": ChannelStats(500, 90), "paid": ChannelStats(2000, 120)}
    a = information_gain_attribution(ch)["channels"]
    assert a["organic"]["share"] > a["paid"]["share"]   # info gain, not raw volume


def test_diversity_drops_as_spend_concentrates():
    assert channel_diversity({"a": 1, "b": 1, "c": 1}) > channel_diversity({"a": 9, "b": 0.5, "c": 0.5})


def test_martech_unit_economics():
    assert cac(10000, 100) == 100.0
    assert cac(10000, 0) == math.inf
    assert roas(30000, 10000) == 3.0
    assert ltv_cac_ratio(400, 100) == 4.0
    assert payback_months(120, 40) == 3.0


def test_below_base_channel_is_still_informative():
    # a channel that converts MUCH worse than base is informative about NON-conversion:
    # information gain credits divergence in either direction (halving 6%->3% > +50% 6%->9%).
    ch = {"organic": ChannelStats(1000, 90), "paid": ChannelStats(1000, 30)}  # base 6%
    a = information_gain_attribution(ch)["channels"]
    assert a["paid"]["share"] > a["organic"]["share"]   # correct info-theoretic behaviour
    assert a["paid"]["lift"] < 1.0 and a["organic"]["lift"] > 1.0


def test_marketing_efficiency_ties_info_to_money():
    # organic diverges MORE from base here (9% vs 6% base) than paid (5% vs 6%), so it earns both
    # the cheaper CAC and the larger information share.
    ch = {"organic": ChannelStats(1000, 90), "paid": ChannelStats(3000, 150)}  # base 6%
    spend = {"organic": 2000, "paid": 9000}
    out = marketing_efficiency(ch, spend, ltv=400, monthly_margin=30)
    assert out["channels"]["organic"]["cac"] < out["channels"]["paid"]["cac"]
    assert out["channels"]["organic"]["info_share"] > out["channels"]["paid"]["info_share"]
    assert abs(out["blended_cac"] - 11000 / 240) < 1e-9
    assert out["mutual_information_bits"] >= 0
