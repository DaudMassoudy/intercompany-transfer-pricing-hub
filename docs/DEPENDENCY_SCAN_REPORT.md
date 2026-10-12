# Dependency Scan Report — v2.0.0-rc.1

## Reproducibility checks

- Python application requirements use exact `==` pins.
- Frontend direct dependencies/devDependencies use exact versions (no `^`, `~`, `*`, `<`, `>` ranges).
- Docker Compose service images use explicit versioned tags; no `:latest` production service tag is present.

## Vulnerability feed limitation

A current CVE/advisory-backed dependency scan could not be executed in this offline build environment because external package vulnerability feeds are unavailable. This report therefore does **not** claim “zero CVEs.”

Run in networked CI before production promotion:

- `pip-audit` or equivalent Python advisory scanner.
- `npm audit --omit=dev` or enterprise JS dependency scanner.
- container image scan (e.g. Trivy/Grype/approved enterprise scanner).
- secret scan and SAST.

Any Critical/High finding must be remediated or formally risk-accepted according to organizational policy before production.
