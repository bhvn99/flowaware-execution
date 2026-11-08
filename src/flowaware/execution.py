"""A single-symbol desk with a shared gross budget and a finite synthetic book."""
from decimal import Decimal, ROUND_FLOOR

from .models import (ChildOrder, DecisionContext, Fill, MarketEvent, OrderState,
                     OrderView, ParentOrder, Quote)


class ExecutionEngine:
    def __init__(self, orders: list[ParentOrder], participation: float = 0.10, child_ttl: int = 2):
        if not orders or len({o.order_id for o in orders}) != len(orders):
            raise ValueError("Need nonempty, uniquely identified parents")
        if not 0 <= participation <= 1 or type(child_ttl) is not int or child_ttl < 1:
            raise ValueError("Invalid participation or child lifetime")
        self.orders = {o.order_id: OrderState(o) for o in orders}
        self.participation = Decimal(str(participation))
        self.child_ttl = child_ttl
        self.children: dict[str, ChildOrder] = {}
        self.fills: list[Fill] = []
        self.events: list[dict] = []
        self.trace: list[dict] = []
        self.market: MarketEvent | None = None
        self.capacity = 0
        self.used = 0
        self.book: dict[str, list[list[int]]] = {}

    def submit(self, parent_id: str, quantity: int) -> str:
        if self.market is None:
            raise ValueError("Begin a market event before submitting")
        state = self.orders[parent_id]
        order, t = state.order, self.market.t
        if not order.arrival <= t < order.deadline:
            raise ValueError("Parent is not active")
        if type(quantity) is not int or not 0 < quantity <= state.available:
            raise ValueError("Child would exceed the available parent quantity")
        child_id = f"C{len(self.children) + 1:06d}"
        self.children[child_id] = ChildOrder(
            child_id, parent_id, quantity, quantity, t, min(t + self.child_ttl, order.deadline)
        )
        state.reserved += quantity
        self.events.append(dict(t=t, event="submit", child_id=child_id, parent_id=parent_id,
                                quantity=quantity))
        self.assert_invariants()
        return child_id

    def cancel(self, child_id: str, reason: str = "cancelled") -> None:
        if reason not in ("cancelled", "expired"):
            raise ValueError("Unknown cancellation reason")
        child = self.children[child_id]
        if child.status != "open":
            return
        self.orders[child.parent_id].reserved -= child.remaining
        child.status = reason
        self.events.append(dict(t=self.market.t if self.market else -1, event=reason,
                                child_id=child_id, parent_id=child.parent_id, quantity=child.remaining))
        self.assert_invariants()

    def begin_event(self, market: MarketEvent) -> None:
        if self.market is not None and market.t != self.market.t + 1:
            raise ValueError("Events must be consecutive")
        if self.market is None and market.t != 0:
            raise ValueError("First event must be time zero")
        self.market = market
        self.capacity = int((self.participation * market.observed_volume).to_integral_value(rounding=ROUND_FLOOR))
        self.used = 0
        self.book = {"buy": [[q.price_cents, q.quantity] for q in market.asks],
                     "sell": [[q.price_cents, q.quantity] for q in market.bids]}
        for child in self.children.values():
            if child.status == "open" and market.t >= child.expires:
                self.cancel(child.child_id, "expired")

    def match(self) -> None:
        if self.market is None:
            raise ValueError("No market event")
        for child in self.children.values():
            if child.status != "open":
                continue
            state = self.orders[child.parent_id]
            order = state.order
            for level in self.book[order.side]:
                price, depth = level
                allowed = price <= order.limit_cents if order.side == "buy" else price >= order.limit_cents
                if not allowed:
                    break  # Quotes are sorted from best to worst.
                quantity = min(child.remaining, depth, self.capacity - self.used)
                if quantity <= 0:
                    continue
                self.fills.append(Fill(self.market.t, child.child_id, child.parent_id,
                                       order.side, quantity, price))
                child.remaining -= quantity
                state.reserved -= quantity
                state.filled += quantity
                self.used += quantity
                level[1] -= quantity
                if child.remaining == 0:
                    child.status = "filled"
                    break
        self.assert_invariants()

    def context(self) -> DecisionContext:
        if self.market is None:
            raise ValueError("No market event")
        market = MarketEvent(self.market.t, self.market.mid_cents, self.market.observed_volume,
                            tuple(Quote(p, q) for p, q in self.book["sell"] if q),
                            tuple(Quote(p, q) for p, q in self.book["buy"] if q))
        # Outstanding children have first claim on subsequent capacity. Do not add
        # further commitments until their reservations fit in this event's allowance.
        outstanding = sum(s.reserved for s in self.orders.values())
        return DecisionContext(market, tuple(OrderView(s.order, s.filled, s.reserved)
            for s in self.orders.values() if s.order.arrival <= market.t < s.order.deadline
            and s.available > 0), max(0, self.capacity - self.used - outstanding))

    def assert_invariants(self) -> None:
        if self.used > self.capacity:
            raise AssertionError("Desk participation exceeded")
        for parent_id, state in self.orders.items():
            reserved = sum(c.remaining for c in self.children.values()
                           if c.parent_id == parent_id and c.status == "open")
            if state.reserved != reserved or min(state.filled, state.reserved, state.available) < 0:
                raise AssertionError("Parent quantity/reservation accounting failed")
        if any(q < 0 for side in self.book.values() for _, q in side):
            raise AssertionError("Visible liquidity consumed twice")

    def run(self, path: list[MarketEvent], policy) -> "ExecutionEngine":
        if not path or path[-1].t < max(s.order.deadline for s in self.orders.values()):
            raise ValueError("Path must include every parent's expiry valuation event")
        for event in path:
            self.begin_event(event)
            self.match()  # FIFO existing children receive first access to the refreshed book.
            context = self.context()
            allocation = policy(context)
            if any(type(q) is not int or q < 0 for q in allocation.values()):
                raise ValueError("Policy allocations must be nonnegative integers")
            if sum(allocation.values()) > context.capacity:
                raise ValueError("Policy requested more than the shared available capacity")
            for parent_id, quantity in allocation.items():
                if quantity:
                    self.submit(parent_id, quantity)
            self.match()
            for state in self.orders.values():
                self.trace.append(dict(t=event.t, parent_id=state.order.order_id,
                                       filled=state.filled, reserved=state.reserved,
                                       available=state.available, capacity=self.capacity,
                                       desk_filled_this_event=self.used))
        return self
