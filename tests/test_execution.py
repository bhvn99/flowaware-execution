from dataclasses import replace
import pytest

from flowaware.execution import ExecutionEngine
from flowaware.models import MarketEvent, ParentOrder, Quote
from flowaware.strategies import POLICIES, deadline_priority
from flowaware.market import generate_market, parent_orders
from flowaware.metrics import audit


def event(t=0, volume=100, depth=20, mid=10000):
    return MarketEvent(t, mid, volume, (Quote(mid - 1, depth),), (Quote(mid + 1, depth),))


def order(key="A", side="buy", quantity=100, arrival=0, deadline=3, limit=None):
    return ParentOrder(key, key, side, quantity, arrival, deadline,
                       limit if limit is not None else (10100 if side == "buy" else 9900))


def test_partial_fill_cancel_releases_only_unfilled_reservation():
    engine = ExecutionEngine([order()], participation=1)
    engine.begin_event(event(depth=20))
    child = engine.submit("A", 50)
    engine.match()
    assert (engine.orders["A"].filled, engine.orders["A"].reserved, engine.orders["A"].available) == (20, 30, 50)
    engine.cancel(child)
    engine.cancel(child)  # Idempotent acknowledgement/retry.
    assert (engine.orders["A"].filled, engine.orders["A"].reserved, engine.orders["A"].available) == (20, 0, 80)
    engine.submit("A", 80)
    with pytest.raises(ValueError):
        engine.submit("A", 1)


def test_simultaneous_children_cannot_reserve_parent_twice():
    engine = ExecutionEngine([order()])
    engine.begin_event(event())
    engine.submit("A", 60)
    engine.submit("A", 40)
    with pytest.raises(ValueError):
        engine.submit("A", 1)
    assert engine.orders["A"].reserved == 100


def test_shared_gross_capacity_counts_both_sides():
    engine = ExecutionEngine([order("A"), order("B", "sell")], participation=.10)
    engine.begin_event(event(volume=100, depth=100))
    engine.submit("A", 6)
    engine.submit("B", 7)
    engine.match()
    assert [f.quantity for f in engine.fills] == [6, 4]
    assert engine.used == 10
    assert engine.orders["B"].reserved == 3


def test_two_clients_share_the_same_book_and_cannot_reuse_depth():
    engine = ExecutionEngine([order("A"), order("B")], participation=1)
    engine.begin_event(event(depth=8))
    engine.submit("A", 6)
    engine.submit("B", 6)
    engine.match()
    engine.match()
    assert sum(f.quantity for f in engine.fills) == 8
    assert engine.orders["B"].reserved == 4


@pytest.mark.parametrize("side,prices,limit,expected", [
    ("buy", (10001, 10003, 10005), 10003, 7),
    ("sell", (9999, 9997, 9995), 9997, 7),
])
def test_walks_levels_but_never_breaches_price_limit(side, prices, limit, expected):
    quotes = tuple(Quote(p, q) for p, q in zip(prices, (3, 4, 20)))
    e = event(volume=1000)
    e = replace(e, **({"asks": quotes} if side == "buy" else {"bids": quotes}))
    engine = ExecutionEngine([order(side=side, limit=limit)], participation=1)
    engine.begin_event(e)
    engine.submit("A", 10)
    engine.match()
    assert engine.orders["A"].filled == expected
    assert engine.orders["A"].reserved == 3


def test_arrival_deadline_and_expiry_boundaries():
    engine = ExecutionEngine([order(arrival=1, deadline=2)], participation=1)
    engine.begin_event(event())
    with pytest.raises(ValueError):
        engine.submit("A", 1)
    engine.begin_event(event(t=1, depth=0))
    child = engine.submit("A", 100)
    engine.match()
    engine.begin_event(event(t=2, depth=100))
    engine.match()
    assert engine.children[child].status == "expired"
    assert engine.orders["A"].reserved == 0
    assert not engine.fills
    with pytest.raises(ValueError):
        engine.submit("A", 1)


def test_zero_volume_and_no_depth_do_not_create_fills():
    for volume, depth in ((0, 100), (100, 0)):
        engine = ExecutionEngine([order()], participation=1)
        engine.begin_event(event(volume=volume, depth=depth))
        engine.submit("A", 20)
        engine.match()
        assert not engine.fills
        assert engine.orders["A"].reserved == 20


def test_fractional_capacity_uses_exact_floor():
    engine = ExecutionEngine([order()], participation=.58)
    engine.begin_event(event(volume=100))
    assert engine.capacity == 58


@pytest.mark.parametrize("policy", POLICIES.values(), ids=POLICIES)
@pytest.mark.parametrize("scenario", ["normal", "liquidity_drought", "thin_book", "overloaded"])
def test_seeded_stress_paths_preserve_all_invariants(policy, scenario):
    for seed in (0, 1, 2):
        path = generate_market(seed, scenario)
        engine = ExecutionEngine(parent_orders(scenario)).run(path, policy)
        assert audit(engine, path) == []
        assert all(s.reserved == 0 for s in engine.orders.values())
        assert all(s.filled <= s.order.quantity for s in engine.orders.values())


@pytest.mark.parametrize("policy", POLICIES.values(), ids=POLICIES)
def test_changing_future_market_cannot_change_past_fills(policy):
    original = generate_market(2)
    alternate = original[:15] + generate_market(3, "falling")[15:]
    a = ExecutionEngine(parent_orders("normal")).run(original, policy)
    b = ExecutionEngine(parent_orders("normal")).run(alternate, policy)
    assert [f for f in a.fills if f.t < 15] == [f for f in b.fills if f.t < 15]
    assert [e for e in a.events if e["t"] < 15] == [e for e in b.events if e["t"] < 15]


@pytest.mark.parametrize("qty", [-1, 0, 1.5, True])
def test_invalid_order_quantity_rejected(qty):
    with pytest.raises(ValueError):
        order(quantity=qty)


def test_invalid_config_and_policy_rejected():
    with pytest.raises(ValueError):
        ExecutionEngine([order(), order()])
    with pytest.raises(ValueError):
        ExecutionEngine([order()], participation=1.1)
    with pytest.raises(ValueError):
        order(deadline=0)
    with pytest.raises(ValueError):
        ParentOrder("A", "A", "buy", 10, 0, 3, 10100, priority=0)


def test_engine_rejects_policy_overbooking():
    with pytest.raises(ValueError, match="shared"):
        ExecutionEngine([order()]).run([event(t=t) for t in range(4)], lambda ctx: {"A": 1000})


def test_path_must_reach_expiry_and_be_consecutive():
    with pytest.raises(ValueError, match="expiry"):
        ExecutionEngine([order()]).run([event()], deadline_priority)
    with pytest.raises(ValueError, match="consecutive"):
        ExecutionEngine([order()]).run([event(), event(t=3)], deadline_priority)
