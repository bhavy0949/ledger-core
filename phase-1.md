# Phase 1 — Repository Scaffold & Configuration

## Objective

Generate the complete directory skeleton, Django project structure, configuration wiring, and infrastructure boilerplate for the **Distributed Transactional Ledger Core**, following the specification in `readme.md` exactly.

---

## Step-by-Step Execution

### Step 1: Directory Tree Creation

Created every folder and subfolder as specified in the `readme.md` section 2 ("Codebase Directory Structure"):

```
src/ledger_core/
src/ledger_core/settings/
src/authentication/
src/ledger/
src/tasks/
CICD/
ansible/group_vars/
ansible/roles/host-hardening/
ansible/roles/docker-bootstrap/
kubernetes/
```

Leaf directories were created with a single `mkdir -p` command. No files were mixed across boundaries — application code, CI/CD, provisioning, and orchestration each have their own root-level directory.

---

### Step 2: Django Project Core (`src/ledger_core/`)

The Django project is named `ledger_core` and lives under `src/`. It was **not** generated via `django-admin startproject` because the spec demands a custom settings-splitting layout. Instead each file was written directly.

#### `ledger_core/__init__.py`
Empty package marker.

#### `ledger_core/settings/__init__.py`
Loads `.env` via `python-dotenv`, then reads `DJANGO_ENV`:
- `dev` → loads `dev.py`
- `prod` → loads `prod.py`

This is the standard environment-based settings split pattern used in production Django deployments.

#### `ledger_core/settings/base.py`
Contains all shared configuration:

| Concern | Implementation |
|---------|---------------|
| **Secret Key** | `DJANGO_SECRET_KEY` env var, no fallback in prod |
| **Database** | PostgreSQL 16+ via `psycopg2-binary`, `CONN_MAX_AGE=60`, `connect_timeout=10` |
| **Redis Cache** | `django-redis` with configurable `REDIS_URL` and 100-max connection pool |
| **Celery** | Broker + result backend from `REDIS_URL`, JSON serialization, 300s task time limit, retry on startup |
| **DRF** | JWT auth as default, JSON-only renderer/parser, custom exception handler |
| **SimpleJWT** | RS256 algorithm, `VERIFYING_KEY` loaded from `JWT_PUBLIC_KEY_PATH`, access token TTL 15 min, refresh TTL 1 day |
| **CORS** | `django-cors-headers`, configurable origins list |
| **Logging** | JSON-formatted console output at configurable level |

#### `ledger_core/settings/dev.py`
Extends `base.py`:
- `DEBUG = True`
- `ALLOWED_HOSTS = ["*"]`
- Adds `drf-spectacular` + `django-extensions`
- Enables `drf-spectacular` schema generation
- Opens CORS to all origins

#### `ledger_core/settings/prod.py`
Extends `base.py`:
- `DEBUG = False`
- Enforces `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- 1-year HSTS with subdomain inclusion and preload
- Sets `SECURE_PROXY_SSL_HEADER` for ELB/ingress termination

#### `ledger_core/urls.py`
Top-level URL dispatcher:
- `/admin/` → Django admin
- `/api/auth/` → `authentication` app
- `/api/ledger/` → `ledger` app

#### `ledger_core/wsgi.py`
Standard WSGI entrypoint, defaults to `prod` environment.

#### `ledger_core/asgi.py`
Standard ASGI entrypoint, defaults to `prod` environment.

#### `ledger_core/celery.py`
Creates the Celery singleton app named `"ledger_core"`, reads config from Django settings under the `CELERY_` namespace, and calls `autodiscover_tasks()` so tasks defined in any `INSTALLED_APPS` are automatically registered.

#### `ledger_core/exceptions.py`
Custom DRF exception handler that wraps error responses in `{"error": true, "detail": ...}`.

---

### Step 3: Django Apps

Three apps matching the spec:

#### `authentication/`
- `apps.py` — `AuthenticationConfig`
- `urls.py` — empty placeholder for JWT endpoints (token obtain/refresh/verify)
- `middleware.py` — empty placeholder for cookie-based token handling
- `models.py`, `serializers.py`, `views.py` — minimal placeholders

#### `ledger/`
- `apps.py` — `LedgerConfig`
- `urls.py` — empty placeholder for transaction/account endpoints
- `models.py`, `serializers.py`, `views.py` — minimal placeholders

#### `tasks/`
- `apps.py` — `TasksConfig`
- `tasks.py` — contains a `@shared_task` placeholder that will be replaced with the idempotent double-entry processing logic

---

### Step 4: `manage.py`

Standard Django management script. Defaults environment to `dev` so local development works without setting env vars manually.

---

### Step 5: `requirements.txt`

Production-ready dependency list with pinned major versions:

| Category | Packages |
|----------|----------|
| Core | Django 5.x, DRF 3.15+, gunicorn 22+ |
| Database | psycopg2-binary 2.9+ |
| Auth | djangorestframework-simplejwt 5.3+, cryptography 42+, PyJWT 2.8+ |
| Async | celery 5.4+, redis 5.0+ |
| Cache | django-redis 5.4+ |
| CORS | django-cors-headers 4.3+ |
| Environment | python-dotenv 1.0+ |
| Dev/Docs | drf-spectacular 0.27+, django-extensions 3.2+ |
| Testing | pytest 8+, pytest-django, pytest-cov |
| Linting | flake8 7+, black 24+ |

All version bounds use `>=X,<Y` to allow minor/patch upgrades while preventing breaking major bumps.

---

### Step 6: Dockerfiles

#### `Dockerfile.api`

Multi-stage build (`python:3.11-slim`):

1. **Build stage** — installs `gcc` + `libpq-dev`, compiles Python wheels
2. **Runtime stage** — copies only wheels, installs without build deps, creates non-root `django` user, copies `src/` contents, mounts `/etc/keys` for JWT public key, runs gunicorn with 4 workers / 2 threads on port 8000

#### `Dockerfile.worker`

Same multi-stage pattern. Runtime starts Celery worker:
```
celery -A ledger_core worker --loglevel=info --concurrency=4 --max-tasks-per-child=1000 --time-limit=300
```

Both images run as `django` user (non-root) and set `PYTHONDONTWRITEBYTECODE`, `PYTHONUNBUFFERED`, `DJANGO_ENV=prod`.

---

### Step 7: Infrastructure Files

#### `CICD/Jenkinsfile`

Declarative pipeline with 5 stages:

| Stage | Action |
|-------|--------|
| Check & Lint | `pip install -r`, `flake8`, `black --check` |
| Static Test | `pytest --cov` with XML coverage |
| Security Scan | `safety check` on dependencies, `trivy` on container images |
| Compile & Push | Docker build + push for both `Dockerfile.api` and `Dockerfile.worker` to AWS ECR |
| Cluster Rollout | `kubectl set image` on both deployments, `kubectl rollout status` |

#### `ansible/`

- **`site.yml`** — entry playbook applying both roles to all hosts
- **`group_vars/all.yml`** — sysctl values (`fs.file-max=2097152`, `net.core.somaxconn=65535`) and docker user list
- **`roles/host-hardening/tasks/main.yml`** — applies kernel parameters via `sysctl` module
- **`roles/docker-bootstrap/tasks/main.yml`** — installs Docker Engine via official apt repository, starts daemon, adds users to `docker` group

#### `kubernetes/`

- **`api-deployment.yaml`** — 2 replicas, `terminationGracePeriodSeconds: 30`, init container runs `migrate`, JWT key volume mount, liveness/readiness probes, CPU/memory resource requests+limits. Includes ClusterIP service on port 80 → 8000.
- **`worker-deployment.yaml`** — 2 replicas, higher resource limits for compute-heavy Celery tasks
- **`hpa.yaml`** — HorizontalPodAutoscaler targeting `worker-deployment`, 2–10 replicas, 75% CPU utilization target
- **`secrets.yaml`** — Two `Opaque` secrets: `ledger-secrets` (all env vars) and `jwt-keys` (public.pem for RS256 verification)

---

### Step 8: Config & Housekeeping Files

| File | Purpose |
|------|---------|
| `.env.example` | Documents every environment variable the system expects |
| `.gitignore` | Excludes `__pycache__`, `.env`, IDE files, `.pem` keys, `staticfiles`, SQLite, coverage, build artifacts |
| `.dockerignore` | Excludes git, local config, cache, and docs from Docker build context |

---

### Step 9: Verification

```
$ python manage.py check
System check identified no issues (0 silenced).

$ python -c "
from ledger_core.celery import app
print(app.main)                    # ledger_core
print(app.conf.task_serializer)    # json
from django.conf import settings
print(settings.INSTALLED_APPS)     # includes authentication, ledger, tasks
print(settings.DATABASES['default']['ENGINE'])  # postgresql
print(settings.SIMPLE_JWT['ALGORITHM'])          # RS256
print(settings.CACHES['default']['BACKEND'])     # django_redis.cache.RedisCache
print(settings.CELERY_BROKER_URL)                # redis://localhost:6379/0
"
```

All wiring validated — settings splitting, Celery, DRF, SimpleJWT, Redis cache, PostgreSQL connectivity, and app registry.

---

## File Count

```
39 files created across 12 directories
```

| Directory | Files |
|-----------|-------|
| `src/` | 4 (manage.py, requirements.txt, 2 Dockerfiles) |
| `src/ledger_core/` | 5 (+ settings/ with 4 files) |
| `src/authentication/` | 6 |
| `src/ledger/` | 6 |
| `src/tasks/` | 3 |
| `CICD/` | 1 |
| `ansible/` | 4 |
| `kubernetes/` | 4 |
| root | 4 (.env.example, .gitignore, .dockerignore, readme.md) |

---

**Business logic has not been implemented yet.** This phase provides the complete, runnable shell that models, views, serializers, Celery tasks, and all domain logic will be plugged into.
