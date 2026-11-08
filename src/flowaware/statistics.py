"""Paired seed bootstrap: clients/ticks are not independent observations."""
import numpy as np
import pandas as pd


def paired_statistics(runs: pd.DataFrame, resamples: int = 2000, seed: int = 987654) -> pd.DataFrame:
    metrics = {"is_bps": (1, "bps"), "completion": (100, "percentage_points"),
               "worst_client_completion": (100, "percentage_points")}
    if resamples < 100:
        raise ValueError("Use at least 100 bootstrap resamples")
    if runs.duplicated(["scenario", "seed", "policy"]).any():
        raise ValueError("Duplicate scenario/seed/policy rows")
    rng, rows = np.random.default_rng(seed), []
    for scenario, group in runs.groupby("scenario", sort=True):
        for metric, (scale, unit) in metrics.items():
            wide = group.pivot(index="seed", columns="policy", values=metric).sort_index()
            required = ["flowaware", "independent_twap", "deadline_priority"]
            if not set(required).issubset(wide.columns) or wide[required].isna().any().any() or len(wide) < 2:
                raise ValueError("Need complete policy pairs on at least two seeds")
            if not np.isfinite(wide[required].to_numpy()).all():
                raise ValueError("Nonfinite comparison metric")
            for baseline in required[1:]:
                delta = (wide["flowaware"] - wide[baseline]).to_numpy() * scale
                means = rng.choice(delta, size=(resamples, len(delta)), replace=True).mean(axis=1)
                low, high = np.quantile(means, [.025, .975])
                better = delta < 0 if metric == "is_bps" else delta > 0
                rows.append(dict(scenario=scenario, metric=metric, baseline=baseline, unit=unit,
                                 flowaware_mean=wide.flowaware.mean() * scale,
                                 baseline_mean=wide[baseline].mean() * scale,
                                 mean_difference=delta.mean(), ci_low=low, ci_high=high,
                                 fraction_better=better.mean(), seeds=len(delta)))
    return pd.DataFrame(rows)
