"""All policies see the same present information and use the same fill engine."""
import math
from .models import DecisionContext, OrderView


def eligible(context: DecisionContext) -> list[OrderView]:
    result = []
    for state in context.orders:
        book = context.market.asks if state.order.side == "buy" else context.market.bids
        if not book:
            continue
        p = book[0].price_cents
        if (state.order.side == "buy" and p <= state.order.limit_cents) or (
            state.order.side == "sell" and p >= state.order.limit_cents
        ):
            result.append(state)
    return sorted(result, key=lambda s: s.order.order_id)


def proportional(demands: dict[str, int], budget: int) -> dict[str, int]:
    """Exact integer largest-remainder rationing with deterministic ID tie breaks."""
    total = sum(demands.values())
    if total <= budget:
        return demands.copy()
    result = {k: v * budget // total for k, v in demands.items()}
    ranking = sorted(demands, key=lambda k: (-(demands[k] * budget % total), k))
    for k in ranking[:budget - sum(result.values())]:
        result[k] += 1
    return result


def independent_twap(context: DecisionContext) -> dict[str, int]:
    demands = {}
    for s in eligible(context):
        o = s.order
        elapsed = context.market.t - o.arrival + 1
        target = o.quantity * elapsed // (o.deadline - o.arrival)
        demands[o.order_id] = min(s.available, max(0, target - s.filled - s.reserved))
    return proportional(demands, context.capacity)


def deadline_priority(context: DecisionContext) -> dict[str, int]:
    left, result = context.capacity, {}
    for s in sorted(eligible(context), key=lambda s: (s.order.deadline, s.order.order_id)):
        q = min(s.available, left)
        result[s.order.order_id] = q
        left -= q
    return result


def flowaware(context: DecisionContext, urgency_bps: float = 25.0) -> dict[str, int]:
    """Greedy integer allocation for a concave one-event surrogate, not global optimal execution.

    Maximise sum_i A_i log(1+q_i) - c_i q_i, subject to shared capacity
    and available quantities. A_i rewards remaining fraction, urgency and schedule lag;
    c_i is displayed best-quote crossing cost per normalised parent share.
    Engine-level fills subsequently enforce actual depth and each price limit.
    """
    if not math.isfinite(urgency_bps) or urgency_bps <= 0:
        raise ValueError("Urgency coefficient must be positive and finite")
    states = eligible(context)
    result = {s.order.order_id: 0 for s in states}
    coefficients = {}
    t, mid = context.market.t, context.market.mid_cents
    for s in states:
        o = s.order
        remaining = o.quantity - s.filled - s.reserved
        target = o.quantity * (t - o.arrival) / (o.deadline - o.arrival)
        lag = max(0.0, target - s.filled - s.reserved) / o.quantity
        a = urgency_bps * o.priority * (remaining / o.quantity) * (1 + lag) / (o.deadline - t)
        quote = context.market.asks[0] if o.side == "buy" else context.market.bids[0]
        c = abs(quote.price_cents - mid) / mid * 10_000 / o.quantity
        coefficients[o.order_id] = (a, c)
    for _ in range(context.capacity):
        best, score = None, 0.0
        for s in states:
            key = s.order.order_id
            q = result[key]
            if q >= s.available:
                continue
            a, c = coefficients[key]
            marginal = a * math.log1p(1 / (q + 1)) - c
            if marginal > score:
                best, score = key, marginal
        if best is None:
            break
        result[best] += 1
    return result


POLICIES = {"independent_twap": independent_twap, "deadline_priority": deadline_priority,
            "flowaware": flowaware}
