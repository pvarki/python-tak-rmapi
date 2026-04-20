# AGENTS.md — python-rasenmaeher-takintegration

## Purpose
The Deploy App (RASENMAEHER) integration bridge for TAK Server. Handles the full TAK user
lifecycle: when a user is enrolled in Deploy App, this service provisions their TAK
certificate, registers them in TAK Server via the REST API, and manages their access.
Also provides a React-based TAK admin web UI embedded in the Deploy App UI. Runs as a
sidecar on the same Docker network as TAK Server.

## Stack & Key Technologies
- **Language:** Python 3.10
- **Framework:** FastAPI + Uvicorn
- **Key libs:** httpx (TAK REST API calls), libpvarki, cryptography
- **Testing:** pytest, tox (25% minimum coverage — lower due to TAK dependency complexity)
- **Linting:** pre-commit, pylint
- **Container:** Docker multi-target (devel_shell, tox, production)
- **Port:** 8003
- **Startup time:** 120+ seconds (certificate generation on first start)

## Development Setup
```bash
export DOCKER_BUILDKIT=1
# Linux:
export DOCKER_SSHAGENT="-v $SSH_AUTH_SOCK:$SSH_AUTH_SOCK -e SSH_AUTH_SOCK"

docker build --ssh default --target devel_shell -t rasenmaeher_takapi:devel_shell .
docker create --name rasenmaeher_takapi_devel -v $(pwd):/app -p 8003:8003 \
  -it $(echo $DOCKER_SSHAGENT) rasenmaeher_takapi:devel_shell
docker start -i rasenmaeher_takapi_devel

# Health check:
takrmapi healthcheck

# Key env vars:
# TAK_HOST, TAK_API_PORT (8443), TAK_ADMIN_CERT_PATH
# TAKSERVER_CERT_PASS, TAK_CA_PASS
```

## Running Tests
```bash
# Via tox (CI)
docker build --ssh default --target tox -t rasenmaeher_takapi:tox .
docker run --rm -it -v $(pwd):/app $(echo $DOCKER_SSHAGENT) rasenmaeher_takapi:tox

# Direct pytest inside devel_shell
pytest tests/ -v --cov=rasenmaeher_takapi --cov-fail-under=25

# Pre-commit
pre-commit install --install-hooks
pre-commit run --all-files
```

## Code Conventions
- Env vars: `TAK_` prefix
- Health check binary: `takrmapi healthcheck` (compose uses this)
- Follow pylint rules from root `pylintrc`
- 25% coverage threshold is intentional — TAK integration tests require a live TAK instance

## Architecture Notes
**Network:** `takrmapi` runs in both `taknet` (shares network with TAK containers) and
`productnet` (accessible to `productsnginx` for the product integration API).

**User lifecycle callbacks** (called by `rmapi` via mTLS through `productsnginx`):
- `POST /api/v1/users/created` — Generates TAK certificate, registers user in TAK Server
- `POST /api/v1/users/revoked` — Revokes TAK certificate, removes user from TAK Server
- `POST /api/v1/users/promoted` — Grants TAK admin role
- `POST /api/v1/users/demoted` — Removes TAK admin role

**Certificate generation:** On user creation, `takrmapi` uses the TAK Server REST API at
`takconfig:8443` to generate a client certificate package (`.zip`) and stores it for
delivery to the user's ATAK/WinTAK device.

**Volumes:** Mounts `tak_data` (TAK cert store), `ui_files` (admin UI static assets),
and `pvarki` (shared credentials from miniwerk manifest).

**Startup:** 120+ second startup time is expected — cert generation takes time on first run.
The health check will not pass until initialization is complete. Do not reduce the
health-check start period without testing.

## Common Agent Pitfalls
1. **120+ second startup is normal.** Do not set health-check timeouts below 180 seconds for
   this service. CI pipelines that wait for this service to be healthy need patience.
2. **TAK certificate changes require TAK volume deletion.** If `TAKSERVER_CERT_PASS` changes,
   delete the TAK volumes — stale JKS files in the volume will cause cert errors that look
   like network failures.
3. **This service shares `taknet` with TAK Server containers.** Direct calls to `takconfig`
   by hostname are expected. These are not public — they only work inside `taknet`.
4. **Coverage threshold is only 25%.** This reflects the difficulty of mocking the TAK
   REST API, not a quality shortcut. New code should still include tests where feasible.
5. **mTLS from `productsnginx` is required.** User lifecycle callbacks arrive with a client
   certificate from `rmapi`. If you bypass `productsnginx` in testing, callbacks will arrive
   without certs and be rejected with `403`.

## Related Repos
- https://github.com/pvarki/docker-rasenmaeher-integration (orchestration root)
- https://github.com/pvarki/docker-rasenmaeher-takserver (TAK Server this bridges)
- https://github.com/pvarki/python-rasenmaeher-api (sends user lifecycle callbacks)
