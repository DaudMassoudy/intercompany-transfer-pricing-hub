# ERP pipeline screenshot and usability update

Screenshots supplied from a local running demo on 12 October 2026. Cropped to the web application viewport without changing the application content.

## Visible states
- ERP / Finance Imports: no imported records; upload and validate action disabled without a file.
- ERP → TP Mapping: five active mapping rules visible; mapping execution available, but no evidence in the screenshots of a completed mapping run.
- Allocation Workbench: one active IT cost allocation rule, no execution runs.
- Segmented P&L Workbench: no snapshots or P&L runs; cube/snapshot buttons disabled.

## Improvements
- Added keyboard operation and accessible name to upload dropzone.
- Explained that demo validation and import use one server request.
- Introduced DE/EN labels and prerequisites on upload/mapping pages.
- Added empty-state guidance for allocations and P&L.
- Allowed the full comma-delimited P&L dimension string to be viewed and edited.
- Added error handling around manual mapping execution.

**Scope:** No changes to authoritative financial calculations, import processing logic, database schema, authorization or ERP adapters. Runtime Docker/end-to-end testing has not been performed.
