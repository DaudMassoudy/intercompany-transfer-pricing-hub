# Test Strategy

1. Unit/golden calculations: ROS, true-up, simulation direction.
2. API vertical slice: auth -> dashboard -> adjustment -> approval -> journal -> simulated posting -> reconciliation -> grounded explanation.
3. Artifact checks: XLSX schema inspection, PDF render validation, JSON/YAML parsing.
4. Package checks: required root files, no secrets/node_modules/cache, ZIP integrity.
5. Future gates: tenant/IDOR security suite, 10m-row load test, live ERP contract test, SSO/UAT, penetration test and backup/DR evidence.
