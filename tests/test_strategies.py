import itertools
import math
from flowaware.models import DecisionContext, MarketEvent, OrderView, ParentOrder, Quote
from flowaware.strategies import proportional, independent_twap, deadline_priority, flowaware


def context(capacity=5):
    orders = (OrderView(ParentOrder("A", "a", "buy", 10, 0, 2, 10100), 0, 0),
              OrderView(ParentOrder("B", "b", "buy", 10, 0, 10, 10100), 0, 0))
    return DecisionContext(MarketEvent(0, 10000, 100, (Quote(9999, 100),), (Quote(10001, 100),)), orders, capacity)


def test_twap_rations_target_deficits_and_deadline_policy_prioritises_urgent():
    assert independent_twap(context()) == {"A": 4, "B": 1}
    assert deadline_priority(context()) == {"A": 5, "B": 0}


def test_proportional_allocation_is_exact_and_deterministic():
    assert proportional({"A": 5, "B": 5, "C": 5}, 8) == {"A": 3, "B": 3, "C": 2}
    assert proportional({}, 0) == {}


def test_flowaware_matches_exhaustive_small_surrogate_optimum():
    ctx = context(5)
    actual = flowaware(ctx)
    # At t=0, lag=0; both parents are wholly outstanding. Cost is 1 bps / 10 shares.
    def utility(q):
        return sum((25 / s.order.deadline) * math.log1p(n) - .1 * n for s, n in zip(ctx.orders, q))
    feasible = [q for q in itertools.product(range(6), repeat=2) if sum(q) <= 5]
    best = max(utility(q) for q in feasible)
    assert math.isclose(utility((actual["A"], actual["B"])), best)


def test_strategy_reproducibility():
    for policy in (independent_twap, deadline_priority, flowaware):
        assert policy(context()) == policy(context())
