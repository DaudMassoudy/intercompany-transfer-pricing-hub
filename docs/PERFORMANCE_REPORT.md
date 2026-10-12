# Performance Report — v2.0.0-rc.1

## Qualification status

**Enterprise-scale performance is NOT QUALIFIED in this RC.1 build environment.**

The target specification calls for validation at 100+ entities, 10m+ financial rows, 100k+ products/SKUs, thousands of allocation rules and hundreds of cost pools. Those volumes were not executed during this upgrade because the host did not provide the intended Docker/PostgreSQL runtime and a representative enterprise dataset was not available.

## Evidence generated in this run

| Evidence | Result |
|---|---|
| 100-test backend regression suite | 5.09 s plain run |
| 100-test run with coverage instrumentation | 7.27 s |
| OpenAPI generation | 87 paths generated successfully |
| PostgreSQL migration generation | Full offline SQL through `0007_configurable_core` generated |

These numbers measure build/test activity, **not product capacity**, and must not be interpreted as transaction throughput or SLA evidence.

## Required production-grade performance gate

A future qualification run should use PostgreSQL and production-like infrastructure and record at minimum: import throughput and memory, mapping-rule evaluation, multi-stage allocation runtime, segmented P&L build, rolling forecast, variance bridge, true-up batch, export performance, API p50/p95/p99, concurrency behavior, database locks, index plans and resource saturation. The run must include failure/retry and idempotency behavior, not only happy-path timing.
