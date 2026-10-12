# Imported-Data P&L & Variance Architecture — v2.0.0-rc.1

## Purpose

RC.7 closes the principal RC.6 data-flow gap: validated and mapped ERP/finance rows can now become the **authoritative operational P&L and calculation source** used by the Control Tower.

## Controlled sequence

`Source file → validation → raw rows → mapping → normalized TP rows → allocation → P&L run → segment P&L → policy-specific PLI → FinancialPeriod operational snapshot → Calculation manifest → Control Tower`

A P&L run is publishable only when:

- accepted rows are fully mapped;
- signed normalized control total reconciles to the accepted source population within EUR/LC 0.01 equivalent precision;
- every active allocation rule has a completed allocation run for the as-of period;
- allocation residual is within configured tolerance;
- an active policy exists for each generated TP segment.

## P&L evidence

Each `pnl_run` stores source imports, source hashes, mapped/unresolved counts, mapping coverage, allocation runs, source/control totals, engine version and creator. Each segment result stores direct revenue, COGS, direct OPEX, allocated OPEX, EBIT, policy-specific PLI, target, status, suggested adjustment and source-row lineage.

## Demonstration dataset

Use `sample_data/20_Authoritative_PnL_Demo.csv` for the controlled RC.7 demo. It contains 500 deterministic finance rows. After running the EUR 1,000,000 Group IT allocation, the imported-data P&L reproduces the reference business results:

- DE01: Revenue EUR 111.9m; COGS EUR 80.0m; OPEX EUR 29.31511m; EBIT EUR 2.58489m; ROS 2.31%; target true-up EUR 1.89111m.
- FR01: ROS 4.00%.
- IT01: ROS 3.013158% (AMBER proximity control).
- PL01: EBIT/TC 7.45234%.
- NL02: Cost Plus 5.263158%.

## Variance decomposition

RC.7 adds an additive deterministic EBIT bridge with two baselines:

- `BUDGET`: actual/YTD result vs approved YTD budget.
- `PRIOR_PERIOD`: imported current period vs immediately preceding imported period.

The supported additive bridge is:

`Revenue impact + COGS impact + Direct OPEX impact + Allocation impact = EBIT variance`

A run is `CONTROLLED` only when the component total reconciles to the total EBIT variance within 0.01.

The platform deliberately does **not** invent volume, sales-price, product-mix or FX effects when the source data does not contain quantity, unit-price, product and FX driver information. Those deeper drivers can be added when source contracts provide the required fields.
