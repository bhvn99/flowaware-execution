# FlowAware: generated research results

All results are synthetic. 1050 evaluation runs: 50 independent seeds ×
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
| falling | deadline_priority | -3.438 | 1.000 | 1.000 | 0.000 | 0 |
| falling | flowaware | -2.325 | 1.000 | 1.000 | 0.000 | 0 |
| falling | independent_twap | -4.680 | 0.995 | 0.980 | 0.125 | 0 |
| liquidity_drought | deadline_priority | 1.572 | 1.000 | 1.000 | 0.000 | 0 |
| liquidity_drought | flowaware | 1.341 | 0.968 | 0.875 | 0.793 | 0 |
| liquidity_drought | independent_twap | 1.094 | 0.831 | 0.553 | 4.214 | 0 |
| normal | deadline_priority | 1.466 | 1.000 | 1.000 | 0.000 | 0 |
| normal | flowaware | 1.364 | 1.000 | 1.000 | 0.000 | 0 |
| normal | independent_twap | 1.220 | 0.998 | 0.993 | 0.040 | 0 |
| overloaded | deadline_priority | 1.712 | 0.918 | 0.744 | 2.057 | 0 |
| overloaded | flowaware | 1.328 | 0.928 | 0.854 | 1.796 | 0 |
| overloaded | independent_twap | 1.238 | 0.888 | 0.713 | 2.801 | 0 |
| rising | deadline_priority | 6.351 | 1.000 | 1.000 | 0.000 | 0 |
| rising | flowaware | 5.013 | 1.000 | 1.000 | 0.000 | 0 |
| rising | independent_twap | 7.097 | 0.994 | 0.974 | 0.138 | 0 |
| thin_book | deadline_priority | 0.676 | 0.361 | 0.136 | 15.966 | 0 |
| thin_book | flowaware | 0.875 | 0.419 | 0.159 | 14.515 | 0 |
| thin_book | independent_twap | 0.880 | 0.419 | 0.032 | 14.515 | 0 |
| wide_spread | deadline_priority | 6.326 | 1.000 | 1.000 | 0.000 | 0 |
| wide_spread | flowaware | 5.957 | 1.000 | 1.000 | 0.000 | 0 |
| wide_spread | independent_twap | 5.420 | 0.998 | 0.993 | 0.040 | 0 |

## Paired comparisons

Negative differences favour FlowAware on economic cost. Confidence intervals resample
independent seeds within each scenario, keeping the policy pairing. They quantify Monte
Carlo variation within this model, not model uncertainty or live-market performance.
Intervals are exploratory and not adjusted for multiple comparisons. Scenarios sharing
seeds are not independent replications to pool into a larger sample count.

| scenario | baseline | mean_delta_bps | ci_low_bps | ci_high_bps | win_fraction | seeds |
| --- | --- | --- | --- | --- | --- | --- |
| falling | independent_twap | 2.356 | 2.150 | 2.565 | 0.000 | 50 |
| falling | deadline_priority | 1.114 | 0.885 | 1.343 | 0.100 | 50 |
| liquidity_drought | independent_twap | 0.247 | 0.108 | 0.390 | 0.280 | 50 |
| liquidity_drought | deadline_priority | -0.231 | -0.604 | 0.151 | 0.600 | 50 |
| normal | independent_twap | 0.143 | -0.056 | 0.376 | 0.420 | 50 |
| normal | deadline_priority | -0.102 | -0.318 | 0.113 | 0.580 | 50 |
| overloaded | independent_twap | 0.090 | 0.013 | 0.167 | 0.320 | 50 |
| overloaded | deadline_priority | -0.384 | -0.776 | 0.040 | 0.660 | 50 |
| rising | independent_twap | -2.084 | -2.316 | -1.847 | 0.980 | 50 |
| rising | deadline_priority | -1.338 | -1.555 | -1.112 | 0.940 | 50 |
| thin_book | independent_twap | -0.005 | -0.073 | 0.060 | 0.440 | 50 |
| thin_book | deadline_priority | 0.199 | 0.081 | 0.317 | 0.280 | 50 |
| wide_spread | independent_twap | 0.537 | 0.322 | 0.739 | 0.300 | 50 |
| wide_spread | deadline_priority | -0.369 | -0.588 | -0.159 | 0.740 | 50 |

The largest observed mean cost disadvantage is **2.356 bps**
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
