# RC.9 Alembic PostgreSQL Startup Fix

RC.8 introduced migration revision `0005_imported_pnl_variance_qualification`. Alembic's default version table stores `version_num` as `VARCHAR(32)`, while that revision ID is longer than 32 characters. PostgreSQL therefore raised `StringDataRightTruncation` while updating `alembic_version`.

RC.9 keeps the same migration operations but uses the revision ID:

`0005_pnl_variance_qual`

This remains chained to `0004_posting_schema_compat` and fits the standard Alembic version column. A regression test now fails the release if any migration revision ID exceeds 32 characters.
