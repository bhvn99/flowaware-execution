import pandas as pd
import pytest
from flowaware.statistics import paired_statistics


def fixture():
    rows = []
    for seed in range(4):
        for policy, cost, completion in [("flowaware", seed - 2, .9),
                                         ("independent_twap", seed, .8),
                                         ("deadline_priority", seed + 1, .85)]:
            rows.append(dict(scenario="example", seed=seed, policy=policy, is_bps=cost,
                             completion=completion, worst_client_completion=completion / 2))
    return pd.DataFrame(rows)


def test_pairing_units_and_known_constant_difference():
    result = paired_statistics(fixture(), 200)
    cost = result[(result.metric == "is_bps") & (result.baseline == "independent_twap")].iloc[0]
    assert cost.mean_difference == cost.ci_low == cost.ci_high == -2
    delivery = result[(result.metric == "completion") & (result.baseline == "independent_twap")].iloc[0]
    assert delivery.mean_difference == pytest.approx(10)
    assert delivery.unit == "percentage_points"
    assert delivery.fraction_better == 1
    pd.testing.assert_frame_equal(result, paired_statistics(fixture().sample(frac=1, random_state=7), 200))


def test_missing_pair_rejected():
    with pytest.raises(ValueError, match="complete"):
        paired_statistics(fixture().iloc[1:], 200)


def test_duplicate_pair_rejected():
    frame = fixture()
    with pytest.raises(ValueError, match="Duplicate"):
        paired_statistics(pd.concat([frame, frame.iloc[:1]]), 200)
