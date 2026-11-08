import math
import pytest

from flowaware.execution import ExecutionEngine
from flowaware.models import Fill, ParentOrder, MarketEvent, Quote
from flowaware.metrics import audit, evaluate
from flowaware.strategies import deadline_priority


@pytest.mark.parametrize("side,fill_price,terminal", [("buy", 10100, 10200), ("sell", 9900, 9800)])
def test_signed_shortfall_includes_unfilled_at_expiry(side, fill_price, terminal):
    order = ParentOrder("P", "Client", side, 10, 0, 1, 11000 if side == "buy" else 9000)
    path = [MarketEvent(0, 10000, 100, (Quote(9900, 4),), (Quote(10100, 4),)),
            MarketEvent(1, terminal, 100, (Quote(terminal - 1, 10),), (Quote(terminal + 1, 10),))]
    engine = ExecutionEngine([order], participation=1).run(path, deadline_priority)
    summary, rows = evaluate(engine, path)
    assert rows[0]["average_fill_price"] == fill_price / 100
    assert rows[0]["trading_cost"] == 4
    assert rows[0]["opportunity_cost"] == 12
    assert summary["is_bps"] == 160
    assert summary["completion"] == .4
    assert summary["non_delivery_penalty_bps"] == 15


def test_no_fill_has_no_average_price_and_signed_opportunity_can_be_negative():
    order = ParentOrder("P", "Client", "buy", 10, 0, 1, 9000)
    path = [MarketEvent(0, 10000, 100, (Quote(9999, 10),), (Quote(10001, 10),)),
            MarketEvent(1, 9900, 100, (Quote(9899, 10),), (Quote(9901, 10),))]
    engine = ExecutionEngine([order], participation=1).run(path, deadline_priority)
    summary, rows = evaluate(engine, path)
    assert math.isnan(rows[0]["average_fill_price"])
    assert summary["completion"] == 0
    assert summary["is_bps"] == -100
    assert summary["non_delivery_penalty_bps"] == 25


def test_audit_detects_corrupted_fill_log():
    order = ParentOrder("P", "Client", "buy", 10, 0, 1, 10001)
    path = [MarketEvent(t, 10000, 100, (Quote(9999, 10),), (Quote(10001, 10),)) for t in range(2)]
    engine = ExecutionEngine([order]).run(path, deadline_priority)
    engine.fills.append(Fill(1, "bad", "P", "sell", 100, 10005))
    errors = audit(engine, path)
    assert "parent timing/side violation" in errors
    assert "price limit violation" in errors
    assert "gross desk capacity violation" in errors
    assert "shared quote depth violation" in errors
    assert "parent fill accounting violation" in errors
