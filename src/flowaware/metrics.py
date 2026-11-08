"""Cost and delivery are reported separately; this is not QTE's scoring formula."""
from collections import defaultdict
from dataclasses import asdict
import math

from .execution import ExecutionEngine
from .models import MarketEvent


def audit(engine: ExecutionEngine, path: list[MarketEvent]) -> list[str]:
    """Recompute fill constraints independently of matching state updates."""
    errors, gross, depth, parent_total = [], defaultdict(int), defaultdict(int), defaultdict(int)
    lookup = {event.t: event for event in path}
    for fill in engine.fills:
        order = engine.orders[fill.parent_id].order
        event = lookup[fill.t]
        if fill.quantity <= 0 or type(fill.quantity) is not int:
            errors.append("invalid fill quantity")
        if not order.arrival <= fill.t < order.deadline or fill.side != order.side:
            errors.append("parent timing/side violation")
        if (order.side == "buy" and fill.price_cents > order.limit_cents) or (
            order.side == "sell" and fill.price_cents < order.limit_cents
        ):
            errors.append("price limit violation")
        gross[fill.t] += fill.quantity
        depth[fill.t, fill.side, fill.price_cents] += fill.quantity
        parent_total[fill.parent_id] += fill.quantity
    for t, q in gross.items():
        if q > int(engine.participation * lookup[t].observed_volume):
            errors.append("gross desk capacity violation")
    for (t, side, price), q in depth.items():
        book = lookup[t].asks if side == "buy" else lookup[t].bids
        if q > sum(level.quantity for level in book if level.price_cents == price):
            errors.append("shared quote depth violation")
    for key, state in engine.orders.items():
        if parent_total[key] != state.filled or parent_total[key] > state.order.quantity:
            errors.append("parent fill accounting violation")
        reserved = sum(c.remaining for c in engine.children.values()
                       if c.parent_id == key and c.status == "open")
        if reserved != state.reserved:
            errors.append("reservation ledger violation")
    for row in engine.trace:
        if min(row["filled"], row["reserved"], row["available"]) < 0 or (
            row["filled"] + row["reserved"] + row["available"] != engine.orders[row["parent_id"]].order.quantity
        ):
            errors.append("quantity conservation violation")
    return errors


def evaluate(engine: ExecutionEngine, path: list[MarketEvent], non_delivery_bps: float = 25.0):
    if not math.isfinite(non_delivery_bps) or non_delivery_bps < 0:
        raise ValueError("Penalty must be finite and nonnegative")
    rows, clients = [], defaultdict(lambda: [0, 0])
    lookup = {event.t: event for event in path}
    for key, state in engine.orders.items():
        o = state.order
        fills = [f for f in engine.fills if f.parent_id == key]
        p0, terminal = lookup[o.arrival].mid_cents, lookup[o.deadline].mid_cents
        sign = 1 if o.side == "buy" else -1
        filled = sum(f.quantity for f in fills)
        unfilled = o.quantity - filled
        trading_cents = sign * sum(f.quantity * (f.price_cents - p0) for f in fills)
        opportunity_cents = sign * unfilled * (terminal - p0)
        notional_cents = o.quantity * p0
        avg = sum(f.quantity * f.price_cents for f in fills) / filled if filled else float("nan")
        row = dict(parent_id=key, client=o.client, side=o.side, quantity=o.quantity, filled=filled,
                   unfilled=unfilled, completion=filled / o.quantity,
                   arrival_price=p0 / 100, terminal_price=terminal / 100,
                   average_fill_price=avg / 100,
                   filled_slippage_bps=sign * (avg - p0) / p0 * 10_000,
                   trading_cost=trading_cents / 100, opportunity_cost=opportunity_cents / 100,
                   implementation_shortfall=(trading_cents + opportunity_cents) / 100,
                   is_bps=10_000 * (trading_cents + opportunity_cents) / notional_cents,
                   notional=notional_cents / 100, unfilled_notional=unfilled * p0 / 100)
        rows.append(row)
        clients[o.client][0] += filled
        clients[o.client][1] += o.quantity
    total_notional = sum(r["notional"] for r in rows)
    unfilled_notional = sum(r["unfilled_notional"] for r in rows)
    summary = dict(is_bps=10_000 * sum(r["implementation_shortfall"] for r in rows) / total_notional,
                   completion=sum(r["filled"] for r in rows) / sum(r["quantity"] for r in rows),
                   worst_client_completion=min(filled / q for filled, q in clients.values()),
                   non_delivery_penalty_bps=non_delivery_bps * unfilled_notional / total_notional,
                   violations=len(audit(engine, path)))
    return summary, rows


def fill_records(engine: ExecutionEngine):
    return [asdict(f) for f in engine.fills]
