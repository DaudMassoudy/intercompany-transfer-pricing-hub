# Test Report — Intercompany Transfer Pricing Hub v2.4.0-rc.3

QUALIFICATION_STATUS: NOT RUN

## Build-environment evidence

- Targeted v2.4 practicality regression: **11 passed / 0 failed** (`test_practicality_10.py` + `test_practicality_upgrade.py`).
- Previous v2.3 full-suite baseline: **116 passed / 0 failed** before the local-qualification harness was added.
- Full v2.4 regression is intentionally executed by `QUALIFY_10_10.bat` inside the pinned Python 3.12 Docker test runner and this report is then regenerated from that actual local result.

No full v2.4 PASS is claimed before the local qualification run.
