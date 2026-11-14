# Validation record — 2026-11-14

## Backend

- 51 tests passed against PostgreSQL locally and in [GitHub Actions](https://github.com/herick-gomes/efood-api/actions/runs/43602211390).
- 97% line coverage in `shop`, excluding migrations, admin and demo commands.
- Concurrency verified with separate connections: two attempts using one customer/key produce one order; two customers competing for the last unit produce one success and one stock conflict.
- Ruff lint/format, Django checks, migration checks and OpenAPI validation passed.
- Migration execution and static-file collection completed in CI.

## Frontend integration

[Draft integration PR #1](https://github.com/herick-gomes/Efood/pull/1) is ready for review. Its [GitHub Actions run](https://github.com/herick-gomes/Efood/actions/runs/43602214058) passed all 7 new tests across 3 suites, and the production build compiled successfully.

Tests cover JWT handling, refresh failure, absence of card fields, authentication errors and preservation of a checkout key after a failed request. The published frontend's main branch was not changed.

## Limits

A full real-browser walkthrough and mobile visual review have not been completed. Docker Compose and the Windows PowerShell script were prepared but not executed in this workspace. PostgreSQL itself was run directly locally and as a service container in GitHub Actions. No production API hosting, real payments, real delivery or load testing was performed.

Before merging the frontend PR: deploy the API, configure the HTTPS API URL and exact CORS origin, then validate the complete browser flow.
