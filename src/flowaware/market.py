"""Synthetic observed snapshots, not historical quotes or a market impact model."""
import numpy as np
from .models import MarketEvent, ParentOrder, Quote

SCENARIOS = ("normal", "liquidity_drought", "wide_spread", "rising", "falling", "thin_book", "overloaded")


def parent_orders(scenario: str) -> list[ParentOrder]:
    multiplier = 2 if scenario == "overloaded" else 1
    # Quantities and limits are ex ante: no realised future volume is consulted.
    return [ParentOrder("A", "Urgent client", "buy", 600 * multiplier, 0, 20, 10050),
            ParentOrder("B", "Patient client", "buy", 900 * multiplier, 0, 60, 10100),
            ParentOrder("C", "Later client", "buy", 600 * multiplier, 10, 45, 10040),
            ParentOrder("D", "Selling client", "sell", 700 * multiplier, 5, 55, 9950)]


def generate_market(seed: int, scenario: str = "normal", *, spread_scale: int = 1,
                    depth_scale: float = 1.0, level_gap: int = 1) -> list[MarketEvent]:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    if type(spread_scale) is not int or spread_scale < 1 or depth_scale < 0:
        raise ValueError("Invalid spread/depth scale")
    if not np.isfinite(depth_scale) or type(level_gap) is not int or level_gap < 0:
        raise ValueError("Invalid depth scale/level gap")
    rng = np.random.default_rng(seed)
    innovations = rng.normal(0, 1.7, 61)
    volume_noise = rng.lognormal(0, 0.25, 61)
    depths = rng.integers(20, 65, size=(61, 2, 3))
    mid = 10_000.0
    path = []
    for t in range(61):
        if t:
            mid += innovations[t] + {"rising": 0.65, "falling": -0.65}.get(scenario, 0)
        m = max(100, int(round(mid)))
        drought = scenario == "liquidity_drought" and 10 <= t < 35
        # This number represents volume already observed before this decision event.
        observed = int(850 * volume_noise[t] * (0.10 if drought else 1))
        spread = (16 if scenario == "wide_spread" and 10 <= t < 40 else 2) * spread_scale
        scale = depth_scale * (0.10 if scenario == "thin_book" else 1) * (0.35 if drought else 1)
        bids = tuple(Quote(m - spread // 2 - j * level_gap, int(depths[t, 0, j] * scale)) for j in range(3))
        asks = tuple(Quote(m + spread // 2 + j * level_gap, int(depths[t, 1, j] * scale)) for j in range(3))
        path.append(MarketEvent(t, m, observed, bids, asks))
    return path
