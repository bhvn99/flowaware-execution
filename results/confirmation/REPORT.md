# FlowAware: generated research results

All results are synthetic. 2100 evaluation runs: 100 independent seeds ×
7 scenarios × three policies. Parameters were fixed in the configuration;
the evaluation seeds were not used to fit a model. There are also 60
development-seed sensitivity runs. All independent constraint audits found zero violations.

## Cost and completion

Shortfall includes signed opportunity cost for unfilled shares, valued at each parent's
expiry midpoint. Lower shortfall alone does not establish better delivery. Completion
and worst-client completion below are fractions; the separate non-delivery penalty is
an illustrative operational metric, not QTE's published score.

| scenario | policy | is_bps | completion | worst_client_completion | non_delivery_penalty_bps | violations |
| --- | --- | --- | --- | --- | --- | --- |
| falling | deadline_priority | -3.156 | 1.000 | 1.000 | 0.000 | 0 |
| falling | flowaware | -2.259 | 1.000 | 1.000 | 0.000 | 0 |
| falling | independent_twap | -4.682 | 0.995 | 0.982 | 0.113 | 0 |
| liquidity_drought | deadline_priority | 1.607 | 1.000 | 1.000 | 0.000 | 0 |
| liquidity_drought | flowaware | 1.343 | 0.966 | 0.874 | 0.839 | 0 |
| liquidity_drought | independent_twap | 1.076 | 0.830 | 0.554 | 4.260 | 0 |
| normal | deadline_priority | 1.695 | 1.000 | 1.000 | 0.000 | 0 |
| normal | flowaware | 1.372 | 1.000 | 1.000 | 0.000 | 0 |
| normal | independent_twap | 1.206 | 0.999 | 0.995 | 0.025 | 0 |
| overloaded | deadline_priority | 1.511 | 0.915 | 0.734 | 2.134 | 0 |
| overloaded | flowaware | 1.351 | 0.928 | 0.860 | 1.791 | 0 |
| overloaded | independent_twap | 1.251 | 0.888 | 0.717 | 2.805 | 0 |
| rising | deadline_priority | 6.504 | 1.000 | 1.000 | 0.000 | 0 |
| rising | flowaware | 4.987 | 0.999 | 0.996 | 0.020 | 0 |
| rising | independent_twap | 7.110 | 0.990 | 0.956 | 0.240 | 0 |
| thin_book | deadline_priority | 0.847 | 0.357 | 0.132 | 16.082 | 0 |
| thin_book | flowaware | 0.960 | 0.420 | 0.155 | 14.507 | 0 |
| thin_book | independent_twap | 0.957 | 0.421 | 0.034 | 14.485 | 0 |
| wide_spread | deadline_priority | 6.576 | 1.000 | 1.000 | 0.000 | 0 |
| wide_spread | flowaware | 5.967 | 1.000 | 1.000 | 0.000 | 0 |
| wide_spread | independent_twap | 5.408 | 0.999 | 0.995 | 0.025 | 0 |

## Paired comparisons

Negative differences favour FlowAware on economic cost. Confidence intervals resample
independent seeds within each scenario, keeping the policy pairing. They quantify Monte
Carlo variation within this model, not model uncertainty or live-market performance.
Intervals are exploratory and not adjusted for multiple comparisons. Scenarios sharing
seeds are not independent replications to pool into a larger sample count.

| scenario | baseline | mean_delta_bps | ci_low_bps | ci_high_bps | win_fraction | seeds |
| --- | --- | --- | --- | --- | --- | --- |
| falling | independent_twap | 2.422 | 2.243 | 2.609 | 0.000 | 100 |
| falling | deadline_priority | 0.897 | 0.747 | 1.040 | 0.100 | 100 |
| liquidity_drought | independent_twap | 0.267 | 0.139 | 0.389 | 0.290 | 100 |
| liquidity_drought | deadline_priority | -0.264 | -0.513 | -0.032 | 0.570 | 100 |
| normal | independent_twap | 0.166 | -0.009 | 0.342 | 0.450 | 100 |
| normal | deadline_priority | -0.323 | -0.480 | -0.173 | 0.670 | 100 |
| overloaded | independent_twap | 0.100 | 0.059 | 0.142 | 0.320 | 100 |
| overloaded | deadline_priority | -0.160 | -0.416 | 0.106 | 0.550 | 100 |
| rising | independent_twap | -2.123 | -2.320 | -1.934 | 1.000 | 100 |
| rising | deadline_priority | -1.517 | -1.680 | -1.358 | 0.960 | 100 |
| thin_book | independent_twap | 0.003 | -0.030 | 0.039 | 0.510 | 100 |
| thin_book | deadline_priority | 0.113 | 0.016 | 0.213 | 0.410 | 100 |
| wide_spread | independent_twap | 0.558 | 0.399 | 0.712 | 0.270 | 100 |
| wide_spread | deadline_priority | -0.609 | -0.751 | -0.454 | 0.790 | 100 |

The largest observed mean cost disadvantage is **2.422 bps**
against **independent_twap** in **falling**. This is selected from all
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
