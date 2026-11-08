# Independent confirmation plan

Recorded on 8 November 2026 before running confirmation seeds 2000–2099.
Initial results from seeds 1000–1049 were already inspected. Their most useful
application findings motivate the following confirmation checks; they were not
prespecified before the initial experiment.

Freeze models.py, market.py, execution.py, strategies.py and metrics.py unchanged.
Use the same seven scenarios, orders, policy coefficient 25, participation cap 0.10
and child TTL 2. No fitting, parameter search or selective reruns.

Primary descriptive checks:
1. Drought: FlowAware completion minus TWAP completion, in percentage points.
2. Overload: FlowAware worst-client completion minus deadline-priority completion
   of the worst client, in percentage points.
3. Rising prices: FlowAware shortfall minus TWAP shortfall, in basis points.

Report all scenarios and both baselines, including falling-price underperformance,
the better drought completion of deadline priority, and cost/delivery trade-offs.
Bootstrap independent seeds within each scenario (2,000 resamples, 95% percentile
intervals). These are pointwise descriptive intervals without multiplicity correction;
do not market them as proof of universal superiority or out-of-sample market alpha.
Repeated clients/events/policies are not independent market samples.

Reproduce the confirmation outputs in a fresh environment, compare every CSV byte
for byte, and record the result. Record the test count after the actual run. No live
performance, official QTE score, production reliability or realistic passive fills
will be claimed.
