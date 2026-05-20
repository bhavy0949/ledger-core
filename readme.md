You can copy the markdown block below exactly as it is and ingest it as context for any AI development agent (like a Cursor agent, a custom GPT, or a specialized coding assistant). It contains the complete architectural blueprint, technical requirements, configuration rules, and folder structure needed to generate the codebase.

---

# System Architecture & DevOps Specification: High-Throughput Distributed Ledger Core

## 1. System Overview & Objective

The goal is to build an asynchronous, fault-tolerant, and idempotent B2B Transactional Ledger Core. The application uses **Django REST Framework (DRF)** for high-performance ingestion, **Asymmetric JWT** for stateless authentication, and **Celery with Redis** for distributed, double-entry bookkeeping validation. The entire system is automated via **Jenkins**, provisioned using **Ansible**, and orchestrated inside **Kubernetes (AWS EKS)**.

### Target Stack

* **Backend Application:** Python 3.11+ / Django 5.x / Django REST Framework
* **Authentication:** `djangorestframework-simplejwt` (Asymmetric RS256 Public/Private Key)
* **Task Broker & Invalidation Layer:** Redis 7.x
* **Asynchronous Processing:** Celery 5.x
* **Database Engine:** PostgreSQL 16+ (Deployed via AWS RDS or cluster-native StatefulSet)
* **Configuration Management:** Ansible 2.15+ (With Ansible Vault)
* **CI/CD Pipeline:** Jenkins (Declarative Pipeline Syntax)
* **Container Runtime & Orchestration:** Docker / Kubernetes (Horizontal Pod Autoscaling)

---

## 2. Codebase Directory Structure

The repository must follow this absolute directory schema. Do not mix application files with infrastructure configurations:

```text
├── src/                          # Backend Source Code
│   ├── ledger_core/              # Django Main App Settings & Routing
│   ├── authentication/           # JWT Middlewares, Cookie Handlers, Keys
│   ├── ledger/                   # Balance Logic, Invariant Handlers, Views, Models
│   ├── tasks/                    # Celery Tasks (Idempotency & Balance Check)
│   ├── manage.py                 # Django CLI Manager
│   ├── requirements.txt          # App Dependencies
│   ├── Dockerfile.api            # Slim Multi-stage Web Target
│   └── Dockerfile.worker         # Slim Multi-stage Celery Target
│
├── CICD/                         # Delivery Automation
│   └── Jenkinsfile               # Multi-branch Declarative Script
│
├── ansible/                      # Host Provisioning & System Hardening
│   ├── site.yml                  # Entry Playbook
│   ├── group_vars/               # Environment Global Variables
│   └── roles/
│       ├── host-hardening/       # Kernel Optimization & SSH Hardening
│       └── docker-bootstrap/     # Runtime Engine & Docker Daemon Installation
│
└── kubernetes/                   # Pod Orchestration & Scale Manifests
    ├── api-deployment.yaml       # Ingestion Pod Configuration
    ├── worker-deployment.yaml    # Consumer Pod Configuration
    ├── hpa.yaml                  # Queue/CPU Dependent Scaling Rules
    └── secrets.yaml              # Base64/Vault Environmental Mapping

```

---

## 3. Application Architecture & Domain Logic

### Database Schema Requirements

* **Account Model:** `id (UUID)`, `client_id (UUID)`, `balance (Decimal)`, `currency (String)`, `updated_at (Timestamp)`.
* **Transaction Model:** `id (UUID)`, `idempotency_key (UUID, Unique)`, `debit_account (FK)`, `credit_account (FK)`, `amount (Decimal)`, `status (Enum: PENDING, SUCCESS, FAILED)`, `created_at (Timestamp)`.

### Core Engineering Guardrails

1. **Asymmetric Auth:** API routes must use RS256 JWTs. The API pods hold *only* the `public.pem` key to verify signatures statelessly. The auth system holds the private key.
2. **In-Flight Ingestion:** The Django View handling incoming transaction logs must perform validation *only on the schema shape*. It must immediately append the payload to the Redis task queue via `delay()` and return a `202 Accepted` response with the transaction ID.
3. **Strict Double-Entry Invariant:** The Celery processing task must wrap database executions inside a transaction block (`transaction.atomic()`). It must fetch rows using `select_for_update()` to lock account states across replicas, ensuring no transaction processes if it drops an account balance below zero.
4. **Idempotency Engine:** The processing task must evaluate the `idempotency_key` first. If the key exists in PostgreSQL, the execution must safely skip processing and return the existing ledger record status.

---

## 4. Infrastructure & DevSecOps Blueprint

### Container Rules (`Dockerfile.api` & `Dockerfile.worker`)

* Must use a multi-stage compilation flow starting from a lightweight python base (`python:3.11-slim`).
* **Stage 1 (Build):** Installs build dependencies (`gcc`, `libpq-dev`), compiles python wheels, and caches packages.
* **Stage 2 (Runtime):** Copies *only* the compiled wheels and app source files. Does not contain compilers or package builders. Runs under a non-root system user using explicit permissions.

### Host Automation (Ansible Playbook)

* `host-hardening` must tune Linux kernel system variables inside `/etc/sysctl.conf`:
* Set maximum file descriptor allocations: `fs.file-max = 2097152`
* Optimize max socket connection backlogs: `net.core.somaxconn = 65535`


* `docker-bootstrap` must install the Docker container engine and set up a secure daemon execution file.

### Delivery Automation (`Jenkinsfile`)

The pipeline must contain five distinct, sequential declarative blocks:

1. **Stage: Check & Lint:** Installs dependencies and checks compliance via `flake8` and `black --check .`.
2. **Stage: Static Test:** Executes the Django transactional test suites inside an isolated test DB environment via `pytest`.
3. **Stage: Security Scan:** Pulls and reviews the application code via dependency checkers, and scans container images via `Trivy`.
4. **Stage: Compile & Push:** Builds `Dockerfile.api` and `Dockerfile.worker` tags, pushes them to AWS ECR using structural environment variables.
5. **Stage: Cluster Rollout:** Connects to the active cluster environment and forces a rolling update using:
`kubectl set image deployment/api-deployment api-container=ecr_url:tag`

### Orchestration Mechanics (Kubernetes & Scaling)

* **Database Management:** Database schema migrations (`python manage.py migrate`) must run using an `initContainer` or a temporary Kubernetes `Job` block *before* deployment replicas initialize.
* **Graceful Termination:** Django deployments must contain a `terminationGracePeriodSeconds: 30` parameter. Upon catching `SIGTERM`, web pods must stop taking fresh requests but complete existing connection hooks.
* **Auto-Scaling (HPA):** Set up a `HorizontalPodAutoscaler` pointing to the `worker-deployment` targeting a min-replica count of 2 and max of 10. Configure auto-scaling behaviors based on an average target metric utilization threshold of 75% or matching Redis queue backlogs.

---

### 🤖 Agent Command Reference Cheat Sheet

* **To start the application code:** *"Generate the Django configuration files, models, and asymmetric simple-jwt authentication hooks for the `src/` folder matching the Database Schema Requirements."*
* **To start the tasks:** *"Create the idempotent Celery ledger consumer logic inside `src/tasks/` utilizing `transaction.atomic()` and `select_for_update()` locking blocks."*
* **To generate DevOps assets:** *"Generate the multi-stage Dockerfiles and the declarative `Jenkinsfile` outlined in the specification schema."*