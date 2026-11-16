# Vercel deployment

Use the Django framework preset and the repository root. Python is pinned to 3.12.
Vercel detects `manage.py`, reads `config.settings` and uses `config.wsgi.application`.
The project dependencies are declared in `pyproject.toml`; `requirements.txt` remains
available for Docker and pip. CI checks that both manifests match and installs from
`pyproject.toml` into a clean environment before checking Django.

## Environment variables

Configure these in the Vercel project before deploying:

- `DJANGO_SECRET_KEY`: an independently generated random secret. Never commit it.
- `DJANGO_DEBUG=0`.
- `DATABASE_URL`: a persistent PostgreSQL database URL, with TLS as required by the provider.
- `DJANGO_ALLOWED_HOSTS`: the exact API hostname(s), comma-separated, without `https://`.
- `CORS_ALLOWED_ORIGINS`: the frontend origin(s), including `https://`.
- `CSRF_TRUSTED_ORIGINS`: trusted HTTPS origins when using Django Admin.

Do not use the local SQLite fallback as hosted storage. Run migrations against the
intended PostgreSQL database through a controlled release step before using the API;
this dependency fix does not provision a database or run remote migrations.

Vercel handles `collectstatic` automatically for its native Django preset. Do not
add legacy `@vercel/python` rewrites just to solve dependency installation.
Keep any existing custom build settings consistent with the native preset.

## Missing Django during settings discovery

If the log says `Installing required dependencies from pyproject.toml` followed by
`ModuleNotFoundError: No module named 'django'`, use the commit that declares
`[project].dependencies`. A tool-only `pyproject.toml` leaves this installation path
without the project's runtime dependencies. Redeploy the new commit rather than
repeating the old deployment.

A successful dependency install does not by itself confirm database connectivity,
migrations, HTTPS proxy behavior or frontend integration. Validate those on the live
project after its environment is configured.

Reference: https://vercel.com/docs/frameworks/full-stack/django
