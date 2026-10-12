# Governed Legal Entity Master Management — v2.0.0-rc.1

## Purpose
PostgreSQL is the system of record for legal entities. Excel is a controlled bulk-onboarding channel, not the authoritative runtime store.

## In-app lifecycle

**Draft → Submitted → Approved / Rejected → Active master version**

A change request can create, update, deactivate or reactivate a legal entity. The entity code is immutable after creation. Approved states are captured in `entity_versions` with reviewer, effective dates and originating request.

## Maker-checker roles

| Role | Draft / import | Approve |
|---|---:|---:|
| Master Data Steward | Yes | No |
| TP Manager | No | Yes |
| Head of TP | Yes | Yes, but never own request |
| Group Tax Director | Yes | Yes, but never own request |
| Platform Admin | Yes | Yes, but never own request |

The request creator cannot approve the same request, including Platform Admin.

## Required entity fields
- Entity code
- Legal name
- ISO country
- Functional currency
- Group currency
- TP characterization
- ERP system
- ERP company code
- Effective-from date

Optional governed fields include tax jurisdiction, tax rate, customs territory and effective-to date.

## Excel bulk onboarding
`sample_data/01_Entity_Master.xlsx` is supported for preview and staging. Rows are classified as `CREATE`, `UPDATE`, `NO_CHANGE`, or `INVALID`. Invalid rows block bulk request creation. Missing workbook rows never trigger delete/deactivate actions.

## Audit and lineage
Material events include `ENTITY_CHANGE_DRAFTED`, `ENTITY_CHANGE_SUBMITTED`, `ENTITY_MASTER_APPROVED`, `ENTITY_CHANGE_REJECTED`, and `ENTITY_MASTER_BULK_STAGED`. Approved changes contain before/after snapshots in the immutable audit trail.

## Professional control principle
Entity-master maintenance is deliberately separated from transaction-data ingestion. A GL file may reference only controlled entity codes; it cannot silently create a legal entity.
