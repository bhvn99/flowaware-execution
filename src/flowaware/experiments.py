"""Run paired synthetic experiments and regenerate the research artefacts."""
import argparse
from dataclasses import asdict
from functools import partial
import hashlib
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .execution import ExecutionEngine
from .market import generate_market, parent_orders
from .metrics import evaluate, fill_records
from .strategies import POLICIES, flowaware
from .statistics import paired_statistics


def run(config_path: Path, output: Path, seed_count: int | None = None):
    cfg = json.loads(config_path.read_text())
    count = cfg["evaluation_seed_count"] if seed_count is None else seed_count
    if count < 2:
        raise ValueError("Use at least two independent evaluation seeds")
    seeds = list(range(cfg["evaluation_seed_start"], cfg["evaluation_seed_start"] + count))
    if set(seeds) & set(cfg["development_seeds"] + cfg["sensitivity_seeds"]):
        raise ValueError("Development and evaluation seeds overlap")
    tables, figures = output / "tables", output / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    policies = dict(POLICIES, flowaware=partial(flowaware, urgency_bps=cfg["flowaware_urgency_bps"]))
    runs, parents, demo = [], [], []
    for scenario in cfg["scenarios"]:
        for seed in seeds:
            path = generate_market(seed, scenario)
            for name, policy in policies.items():
                engine = ExecutionEngine(parent_orders(scenario), cfg["participation"], cfg["child_ttl"]).run(path, policy)
                summary, rows = evaluate(engine, path, cfg["non_delivery_penalty_bps"])
                if summary["violations"]:
                    raise AssertionError("Independent audit found an execution violation")
                tags = dict(scenario=scenario, seed=seed, policy=name)
                runs.append(dict(**tags, **summary))
                parents.extend(dict(**tags, **r) for r in rows)
                if scenario == "liquidity_drought" and seed == seeds[0]:
                    demo.extend(dict(policy=name, **r) for r in engine.trace)
                    pd.DataFrame(fill_records(engine)).to_csv(tables / f"demo_fills_{name}.csv", index=False)
                    pd.DataFrame(engine.events).to_csv(tables / f"demo_children_{name}.csv", index=False)
                    if name == "flowaware":
                        (output / "demo_market.json").write_text(json.dumps([asdict(e) for e in path], indent=2) + "\n")
    frame = pd.DataFrame(runs)
    frame.to_csv(tables / "runs.csv", index=False)
    pd.DataFrame(parents).to_csv(tables / "parents.csv", index=False)
    trace = pd.DataFrame(demo)
    trace.to_csv(tables / "demo_trace.csv", index=False)
    summary = frame.groupby(["scenario", "policy"], sort=True).agg(
        is_bps=("is_bps", "mean"), completion=("completion", "mean"),
        worst_client_completion=("worst_client_completion", "mean"),
        non_delivery_penalty_bps=("non_delivery_penalty_bps", "mean"),
        violations=("violations", "sum")).reset_index()
    summary.to_csv(tables / "summary.csv", index=False)

    paired = []
    rng = np.random.default_rng(cfg["bootstrap_seed"])
    for scenario, group in frame.groupby("scenario", sort=True):
        wide = group.pivot(index="seed", columns="policy", values="is_bps")
        for baseline in ("independent_twap", "deadline_priority"):
            delta = (wide["flowaware"] - wide[baseline]).to_numpy()
            draws = rng.choice(delta, size=(cfg["bootstrap_resamples"], len(delta)), replace=True).mean(axis=1)
            lo, hi = np.quantile(draws, [.025, .975])
            paired.append(dict(scenario=scenario, baseline=baseline, mean_delta_bps=delta.mean(),
                               ci_low_bps=lo, ci_high_bps=hi, win_fraction=float((delta < 0).mean()), seeds=len(delta)))
    comparisons = pd.DataFrame(paired)
    comparisons.to_csv(tables / "paired_comparisons.csv", index=False)
    paired_statistics(frame, cfg["bootstrap_resamples"], cfg["bootstrap_seed"]).to_csv(
        tables / "paired_metrics.csv", index=False)

    sensitivity = []
    for variant in cfg["sensitivity_variants"]:
        parameters = {k: v for k, v in variant.items() if k != "name"}
        for seed in cfg["sensitivity_seeds"]:
            path = generate_market(seed, "normal", **parameters)
            for name, policy in policies.items():
                engine = ExecutionEngine(parent_orders("normal"), cfg["participation"], cfg["child_ttl"]).run(path, policy)
                metrics, _ = evaluate(engine, path, cfg["non_delivery_penalty_bps"])
                if metrics["violations"]:
                    raise AssertionError("Sensitivity audit failed")
                sensitivity.append(dict(variant=variant["name"], seed=seed, policy=name, **metrics))
    pd.DataFrame(sensitivity).to_csv(tables / "sensitivity.csv", index=False)

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    colors = {"independent_twap": "#8794a5", "deadline_priority": "#e09b38", "flowaware": "#176b87"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5), sharey=True, layout="constrained")
    scenarios = cfg["scenarios"]
    y = np.arange(len(scenarios))
    for i, name in enumerate(policies):
        group = summary[summary.policy == name].set_index("scenario").loc[scenarios]
        position = y + (i - 1) * .24
        axes[0].barh(position, group.is_bps, height=.22, color=colors[name], label=name.replace("_", " "))
        axes[1].barh(position, group.completion * 100, height=.22, color=colors[name])
    axes[0].set(yticks=y, yticklabels=[s.replace("_", " ") for s in scenarios],
                xlabel="Mean shortfall (bps) · lower is cheaper")
    axes[0].invert_yaxis()
    axes[0].axvline(0, color="#888888", linewidth=.7)
    axes[0].legend(loc="lower right", fontsize=8)
    axes[1].set(xlabel="Mean completion (%) · higher is better", xlim=(0, 105))
    fig.suptitle(f"Synthetic cost and delivery · {count} independent paths per scenario")
    fig.savefig(figures / "cost_completion.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(10, 6), sharex=True, layout="constrained")
    quantities = {o.order_id: o.quantity for o in parent_orders("liquidity_drought")}
    for ax, parent_id in zip(axes.flat, quantities):
        for name in policies:
            subset = trace[(trace.parent_id == parent_id) & (trace.policy == name)]
            ax.step(subset.t, subset.filled / quantities[parent_id] * 100, where="post", color=colors[name], label=name)
        ax.axvspan(10, 35, color="#d7e5eb", alpha=.5)
        deadline = next(o.deadline for o in parent_orders("normal") if o.order_id == parent_id)
        ax.axvline(deadline, ls=":", color="#555555")
        ax.set(title=f"Client {parent_id} · expiry {deadline}", xlabel="Synthetic event", ylabel="Completion (%)", ylim=(-2, 105))
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(f"Liquidity drought · preselected example seed {seeds[0]} (shaded period)")
    fig.savefig(figures / "drought_completion.png", dpi=170)
    plt.close(fig)

    chosen = comparisons[comparisons.baseline == "independent_twap"].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    ax.errorbar(chosen.mean_delta_bps, np.arange(len(chosen)),
                xerr=[chosen.mean_delta_bps - chosen.ci_low_bps, chosen.ci_high_bps - chosen.mean_delta_bps],
                fmt="o", color=colors["flowaware"], capsize=4)
    ax.axvline(0, color="#888888", ls="--")
    ax.set(yticks=np.arange(len(chosen)), yticklabels=chosen.scenario.str.replace("_", " "),
           xlabel="FlowAware minus TWAP shortfall (bps) · negative favours FlowAware",
           title="Paired mean differences with 95% seed-bootstrap intervals")
    fig.savefig(figures / "paired_cost_difference.png", dpi=170)
    plt.close(fig)

    def markdown_table(df):
        columns = list(df.columns)
        lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
        for row in df.itertuples(index=False, name=None):
            lines.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in row) + " |")
        return "\n".join(lines)

    worst = comparisons.sort_values("mean_delta_bps", ascending=False).iloc[0]
    report = f"""# FlowAware: generated research results

All results are synthetic. {len(frame)} evaluation runs: {count} independent seeds ×
{len(cfg['scenarios'])} scenarios × three policies. Parameters were fixed in the configuration;
the evaluation seeds were not used to fit a model. There are also {len(sensitivity)}
development-seed sensitivity runs. All independent constraint audits found zero violations.

## Cost and completion

Shortfall includes signed opportunity cost for unfilled shares, valued at each parent's
expiry midpoint. Lower shortfall alone does not establish better delivery. Completion
and worst-client completion below are fractions; the separate non-delivery penalty is
an illustrative operational metric, not QTE's published score.

{markdown_table(summary)}

## Paired comparisons

Negative differences favour FlowAware on economic cost. Confidence intervals resample
independent seeds within each scenario, keeping the policy pairing. They quantify Monte
Carlo variation within this model, not model uncertainty or live-market performance.
Intervals are exploratory and not adjusted for multiple comparisons. Scenarios sharing
seeds are not independent replications to pool into a larger sample count.

{markdown_table(comparisons)}

The largest observed mean cost disadvantage is **{worst['mean_delta_bps']:.3f} bps**
against **{worst['baseline']}** in **{worst['scenario']}**. This is selected from all
predeclared comparisons and must be read alongside delivery. The simulator uses
exogenous price paths: faster completion can cost more in a falling buy market.

## Limits and next experiment

Quotes refresh independently of our orders; deeper fills consume visible levels but
do not move future prices. There is no queue model, passive-fill inference, fees,
latency or real market calibration. The single-event FlowAware objective uses best-quote
cost, not the exact cost of walking every level. Existing children receive FIFO access;
unfilled reservations can temporarily block new allocation. These assumptions affect
all policies and can change the ranking. See sensitivity.csv for doubled spread,
halved depth and steeper quote ladders on development seeds. Do not tune the policy on
these held-out evaluation outcomes. A follow-up should predeclare and test a revised
cost estimator or fairness rule using a fresh evaluation seed range.
"""
    (output / "REPORT.md").write_text(report)
    hashes = {str(p.relative_to(config_path.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((config_path.parent / "src").rglob("*.py"))}
    for p in (config_path, config_path.parent / "requirements.txt"):
        hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = dict(config=cfg, actual_evaluation_seeds=seeds, python=platform.python_version(),
                    numpy=np.__version__, pandas=pd.__version__, matplotlib=matplotlib.__version__, source_sha256=hashes)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Completed {len(frame)} evaluation + {len(sensitivity)} sensitivity runs; zero audited violations.")
    print(f"Outputs: {output.resolve()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("experiment_config.json"))
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--seeds", type=int, default=None, help="Override evaluation seed count for a smoke run")
    args = parser.parse_args()
    run(args.config.resolve(), args.output, args.seeds)


if __name__ == "__main__":
    main()
