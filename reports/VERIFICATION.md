# Verification and claim ledger

Verified 8 November 2026, Python 3.13.5. All data is synthetic.

## Completed checks

- 42 automated test cases passed in the working environment and in a fresh virtual environment.
- 1,050 initial and 2,100 confirmation policy runs completed: 3,150 total, across seven
  scenarios and three policies. Cohorts use disjoint seeds 1000–1049 and 2000–2099.
- Zero violations found by the implemented audit in both cohorts and sensitivity runs.
- The core trading/model/metric files were unchanged for confirmation; only statistics,
  reporting and presentation were extended.
- All 19 generated confirmation files (13 CSVs, three PNGs, market JSON, manifest JSON
  and Markdown report) reproduced **byte-for-byte** in a fresh virtual environment.
  Finder metadata is excluded. Dependencies were installed from a local wheel cache
  using the pinned requirements; cross-platform reproducibility has not been tested.
- The original 12 CSV outputs remained byte-identical after adding delivery statistics.
- All three confirmation figures were visually inspected; overlapping labels in the
  first chart were replaced with separate cost and delivery panels.
- GitHub Actions is configured, but has not run remotely. No live trading is implemented.

Machine-readable checks and fingerprints: [reproducibility.json](reproducibility.json).

## Numerically supported claims

All headline numbers below use **100 new confirmation seeds**, not whichever cohort
produced a more attractive number. Differences are means of paired seed differences.
The intervals are 95% percentile bootstrap intervals, without multiplicity correction.

| Claim | Exact result | Pointwise interval | Evidence |
| --- | --- | --- | --- |
| Improve drought delivery vs TWAP | 82.9582% → 96.6429%; +13.6846 percentage points | +13.4718 to +13.8764 pp | `liquidity_drought`, `completion`, `independent_twap` |
| Improve mean worst-client completion under overload vs deadline priority | 73.4472% → 85.9917%; +12.5445 percentage points | +10.9946 to +13.9960 pp | `overloaded`, `worst_client_completion`, `deadline_priority` |
| Lower shortfall in rising-price scenario vs TWAP | 7.1098 → 4.9871 bps; −2.1228 bps | −2.3187 to −1.9304 bps | `rising`, `is_bps`, `independent_twap` |
| Higher shortfall in falling-price scenario vs TWAP | −4.6816 → −2.2592 bps; +2.4224 bps | +2.2434 to +2.6088 bps | `falling`, `is_bps`, `independent_twap` |

Rows can be located by the three fields in
[paired_metrics.csv](../results/confirmation/tables/paired_metrics.csv).
The all-policy values are in [summary.csv](../results/confirmation/tables/summary.csv).

## Context required when explaining the gains

Completion measures filled shares/requested shares. A 13.7 **percentage-point** gain
is not a 13.7% relative gain. Worst-client completion is the minimum client delivery
within each run, averaged across seeds; the worst client need not be the same client
in each run. Basis points normalise shortfall by requested arrival notional.

Deadline priority achieves 100% drought completion and therefore exceeds FlowAware.
FlowAware drought shortfall is 1.3426 bps versus TWAP's 1.0756 bps: greater delivery
comes with greater measured economic cost here. In rising prices, FlowAware's mean
completion is 99.920%, not exactly 100%. In the thin-book scenario all strategies
complete less than 43%. Never describe the adaptive rule as universally best.

The coefficients and order templates are assumptions, not calibrated estimates.
Shared paths control comparison noise; they do not make the simulation empirical.
No future-data interface is provided to policies. This is supported by the explicit
future-suffix perturbation test, not a claim of formal verification.

## Role relevance

The work demonstrates parent/child order management, quantity reservations, shared
liquidity allocation, price/time constraints, execution monitoring and transaction-cost
analysis. Those are directly connected to the responsibilities on QTE's public
[Execution Arm page](https://queenstowerexchange.com/arms/execution). The four-client,
single-symbol model is an educational abstraction, not QTE's actual system or scoring.

## Claims not supported

Do not claim live trading returns, calibrated market impact, production readiness,
passive queue modelling, a globally optimal full-horizon strategy, 3,150 independent
markets, universal cost savings, an official QTE score, a guarantee of selection, or
that the user has already independently understood/reviewed all generated code.
AI coding assistance is disclosed in the README.
