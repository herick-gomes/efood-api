# Validation record — 2026-11-14

## Backend

- 51 tests passed locally against PostgreSQL 17.11.
- 97% line coverage in `shop`, excluding migrations, admin and demo commands.
- Concurrency verified with separate connections: two attempts using one customer/key produce one order; two customers competing for the last unit produce one success and one stock conflict.
- Ruff lint and format checks passed.
- Django system checks passed; no missing migrations.
- OpenAPI schema validated with `--fail-on-warn`.
- Static-file collection completed.

## Frontend integration

The companion branch in Efood adds tests for JWT handling, refresh failure, absence of card fields, authentication errors and preserving a checkout key after a failed request. Its production bundle is built separately. GitHub verification results and the pull request link will be recorded after publication.

## Limits

A full real-browser walkthrough and mobile visual review have not been completed. Docker Compose and the Windows PowerShell script were prepared but not executed in this Linux workspace. PostgreSQL itself was run directly for backend tests. No production hosting, real payments, real delivery or load testing was performed.

This record distinguishes implemented functionality and automated verification from deployment readiness.
