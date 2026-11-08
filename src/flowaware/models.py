"""Integer prices (cents) and shares make order accounting exact."""
from dataclasses import dataclass
from typing import Literal

Side = Literal["buy", "sell"]


@dataclass(frozen=True)
class ParentOrder:
    order_id: str
    client: str
    side: Side
    quantity: int
    arrival: int
    deadline: int
    limit_cents: int
    priority: float = 1.0

    def __post_init__(self):
        if not self.order_id or not self.client or self.side not in ("buy", "sell"):
            raise ValueError("An order needs identifiers and a valid side")
        for name in ("quantity", "arrival", "deadline", "limit_cents"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer")
        if self.quantity <= 0 or self.limit_cents <= 0 or self.arrival < 0:
            raise ValueError("Quantity/limit must be positive and arrival nonnegative")
        if self.deadline <= self.arrival or not 0 < self.priority < float("inf"):
            raise ValueError("Deadline must follow arrival; priority must be finite and positive")


@dataclass(frozen=True)
class Quote:
    price_cents: int
    quantity: int

    def __post_init__(self):
        if type(self.price_cents) is not int or type(self.quantity) is not int:
            raise ValueError("Quote prices and quantities must be integers")
        if self.price_cents <= 0 or self.quantity < 0:
            raise ValueError("Invalid quote")


@dataclass(frozen=True)
class MarketEvent:
    t: int
    mid_cents: int
    observed_volume: int
    bids: tuple[Quote, ...]
    asks: tuple[Quote, ...]

    def __post_init__(self):
        if type(self.t) is not int or self.t < 0:
            raise ValueError("Invalid event time")
        if type(self.observed_volume) is not int or self.observed_volume < 0:
            raise ValueError("Invalid observed volume")
        if type(self.mid_cents) is not int or self.mid_cents <= 0:
            raise ValueError("Invalid midpoint")
        if any(a.price_cents < b.price_cents for a, b in zip(self.bids, self.bids[1:])):
            raise ValueError("Bids must be descending")
        if any(a.price_cents > b.price_cents for a, b in zip(self.asks, self.asks[1:])):
            raise ValueError("Asks must be ascending")
        if self.bids and self.bids[0].price_cents > self.mid_cents:
            raise ValueError("Bid exceeds midpoint")
        if self.asks and self.asks[0].price_cents < self.mid_cents:
            raise ValueError("Ask below midpoint")


@dataclass
class OrderState:
    order: ParentOrder
    filled: int = 0
    reserved: int = 0

    @property
    def available(self):
        return self.order.quantity - self.filled - self.reserved


@dataclass
class ChildOrder:
    child_id: str
    parent_id: str
    quantity: int
    remaining: int
    submitted: int
    expires: int
    status: str = "open"


@dataclass(frozen=True)
class Fill:
    t: int
    child_id: str
    parent_id: str
    side: Side
    quantity: int
    price_cents: int


@dataclass(frozen=True)
class OrderView:
    """A policy gets a read-only current state, never the engine or future path."""
    order: ParentOrder
    filled: int
    reserved: int

    @property
    def available(self):
        return self.order.quantity - self.filled - self.reserved


@dataclass(frozen=True)
class DecisionContext:
    market: MarketEvent
    orders: tuple[OrderView, ...]
    capacity: int
