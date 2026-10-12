# Transfer Pricing Validation Pack — v2.0.0-rc.1

## Calculation governance

Authoritative amounts use Python `Decimal` with `ROUND_HALF_UP` policy. Money is quantized to 0.01 for authoritative calculation outputs; ratios are quantized to 8 decimal places in the deterministic engine. Calculation manifests record engine/policy/source versions.

## Implemented calculation families

### TNMM — ROS
`ROS = EBIT / Revenue`, with `EBIT = Revenue - COGS - OPEX`.

Target EBIT: `Revenue × Target ROS`.

True-up: `Target EBIT - Actual EBIT`.

### TNMM — EBIT / Total Costs
`EBIT / (COGS + OPEX)`.

Target adjustment: `(Target PLI × Total Costs) - Actual EBIT`.

### Berry Ratio
`Gross Profit / Operating Expenses`.

Implemented only as a deterministic computational option; appropriateness for a real tested party requires professional TP judgment.

### Cost Plus
Markup profit: `Eligible Cost Base × Markup`.

Charge: `Eligible Cost Base + Markup Profit`.

Service charge workflow supports cost-pool exclusions and recipient allocation.

### Resale Price / Resale Minus
Resale margin: `(Resale Revenue - Purchase Cost) / Resale Revenue`.

Target purchase cost: `Resale Revenue × (1 - Target Margin)`.

### CUP framework
Computes controlled-vs-reference price variance. A real CUP analysis requires comparability/adjustment evidence outside the pure calculation engine.

### Profit Split framework
Allocates combined profit by deterministic weights and places rounding residual on the final recipient so allocated total reconciles to combined profit.

### FX
Deterministic amount × configured positive exchange rate. Production use requires governed rate source/type/version.

## Golden validation

69 executable financial/method/allocation test cases pass, including positive/negative/zero true-ups, loss/zero revenue, policy range boundaries, Cost Plus, Resale Price, Berry Ratio, CUP variance, Profit Split, FX, goal-seek, allocation rounding and service-charge cases.

## DE01 reference case

- Revenue: EUR 111,900,000
- COGS: EUR 80,000,000
- OPEX: EUR 29,315,110
- EBIT: EUR 2,584,890
- Actual ROS: 2.31%
- Policy target: 4.00%
- Target EBIT: EUR 4,476,000
- Target true-up: EUR 1,891,110

## External professional validation

The formulas and tests demonstrate deterministic implementation correctness. They do not determine whether a TP method, tested party, PLI, range or target is legally/economically appropriate for a specific taxpayer. Independent TP professional sign-off remains required before production use.
