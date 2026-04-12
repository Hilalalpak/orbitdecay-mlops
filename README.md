# OrbitDecay MLOps

An end-to-end MLOps system I built to predict when LEO satellites will re-enter the atmosphere.

> **Note:** This is a personal portfolio project. I'm uploading the code in parts as I clean things up — not everything is here yet, and some pieces are still being worked on.

---

## What it does

Pulls orbital data from Space-Track.org, combines it with solar flux (NRCan), geomagnetic indices (NOAA), and sunspot number (SIDC), runs it through an ML pipeline, and serves risk predictions via a REST API.

Output is a risk level — **CRITICAL / HIGH / MEDIUM / LOW** — per satellite, plus an estimated days-until-reentry.

I built this because I wanted to work on something with real data and a proper MLOps setup, not just a notebook with a model in it.

---

## Project Roles

Since this is a portfolio project, the main goal wasn't to optimize ML model performance — it was to **design and build a full end-to-end MLOps architecture on my own**. The different layers of the project cover responsibilities that would normally be distributed across separate teams:

**ML Engineer**
The heaviest part of the project — from model to pipeline:
- `src/machine_learning/` — LSTM models
- `src/pipeline/coordinators/phase1-8/` — 8-phase data processing pipeline:
  - Phase 1: Orbital collection → orbit container
  - Phase 2: Orbital processing → orbit_processing container
  - Phase 3: Orbital feature engineering → atmospheric_features container
  - Phase 4: Environmental collection → environment container
  - Phase 5: Environmental processing → environment_processing container
  - Phase 6: Environmental synthesis → environment_synthesis container
  - Phase 7: Time series integration → time_series container
  - Phase 8: Model training → ml container
- `src/domain/orbital/` + Rust plugin — orbital mechanics calculations
- `src/scheduler/daily_reporter.py` — daily prediction scheduler
- MLflow integration — experiment tracking, model registry

**MLOps Engineer**
The bridge between pipeline and infrastructure:
- `src/pipeline/orchestration/` — pipeline orchestration
- `src/pipeline/di_containers/` — dependency injection
- `src/pipeline/monitoring/` — pipeline performance monitoring
- MLflow + MinIO integration
- `infrastructure/config/` — 3-environment config management

**Backend / API Engineer**
- `src/api/` — FastAPI service (prediction, training, health, monitoring endpoints)
- `src/api/state_manager.py` — service startup / graceful degradation
- `src/api/trainer_factory.py` — model training factory
- Prometheus metrics export

**DevOps / Platform Engineer**
- `docker-compose.yml` — 15+ service orchestration
- `infrastructure/docker/images/` — 7 custom Docker images
- `Jenkinsfile` — CI/CD pipeline
- `Jenkinsfile.ml-pipeline` — nightly ML pipeline job (data collection + retraining, parametrized)
- `deploy-dev.sh`, `deploy-prod.sh` — deployment scripts
- Gitea, Jenkins setup

**Monitoring / Observability Engineer**
- `infrastructure/monitoring/prometheus/` — Prometheus config + alert rules
- `infrastructure/monitoring/alertmanager/` — alert routing
- `infrastructure/docker/grafana/` — dashboard + datasource provisioning
- `src/monitoring/prometheus_metrics.py` — custom metrics

**Data Engineer**
- `src/domain/orbital/` — TLE data collection (Space-Track API)
- `src/domain/timeseries/` — time series processing
- `infrastructure/database/` — PostgreSQL schema + backup
- MinIO bucket management

Since this is an MLOps project, all layers are deeply intertwined.

---

## ML Side

### Core Hypothesis

Solar activity directly drives atmospheric density at LEO altitudes. When F10.7 solar flux and geomagnetic indices (Kp, Ap) spike, atmospheric drag increases and orbital decay accelerates. The sunspot number (SIDC) provides long-term solar cycle context — particularly useful for understanding which phase of the ~11-year cycle the system is currently in. The models are built around these relationships.

Atmospheric density is calculated using NRLMSISE-00 rather than simple exponential models. Below 500 km, especially during geomagnetic storms, the difference is significant.

### Framing: Early Warning System, not a Crystal Ball

The goal isn't a single precise reentry timestamp — that's not realistic with the available data. Instead, the system works like a **tiered alert escalation**, similar to DEFCON levels applied to orbital decay:

- Stable orbit → no alert
- Decay rate increasing → watch state
- Projected lifetime dropping rapidly → elevated risk
- Imminent reentry window → critical alert

This matches how Space Situational Awareness (SSA) operations actually work.

### Architecture: Hybrid Physics-Informed LSTM

Standard fixed-interval time series models don't work well here — TLE observations are **irregularly sampled**. A satellite might have 3 observations one week and 12 the next.

To handle this, the model uses a **dual-branch architecture**:

- **Branch 1 (Temporal)** — LSTM with explicit `delta_t` (time since last observation) as an input feature, so the model learns from the gap between observations, not just the values
- **Branch 2 (Static)** — processes time-invariant orbital parameters (BSTAR drag coefficient, inclination, eccentricity) separately

Outputs are merged before the final risk classification head. This is closer to a Time-Aware LSTM / Neural ODE approach than a standard sequence model.

Feature engineering lives in its own domain layer (`src/domain/orbital/features/`) — generators for orbital mechanics, space weather coupling, and telemetry-derived metrics.

---

## Infrastructure

I wanted this to feel like a real production system, not a demo, so I set up the full stack:

**Data & Storage**
- PostgreSQL 16 — main database and MLflow backend store
- MinIO — S3-compatible object storage for model artifacts and large datasets

**MLOps**
- MLflow — experiment tracking and model registry

**API**
- FastAPI — serves predictions, exposes `/metrics` endpoint for Prometheus

**Observability**
- Prometheus + Grafana + Alertmanager
- Tracks API latency, prediction throughput, Space-Track quota usage

**CI/CD**
- Self-hosted Gitea + Jenkins
- Push to `dev` → runs dev tests → auto-merges to `test`
- Push to `test` → runs integration tests → auto-merges to `main`
- Push to `main` → manual approval gate → `./deploy-prod.sh`

**Environments**
- `dev`, `test`, `prod` are isolated Docker Compose profiles
- Each has its own API container with SSH access for Jenkins

There's also a scheduler that generates a daily report at 17:30 (Istanbul time) with prediction summaries and API health.

---

## Service Architecture

The system runs in isolation per environment using Docker Compose profiles (`dev`, `test`, `prod`, `pipeline`).

### Core Infrastructure

**`postgres`** — Runs in all environments. Both the main application database and MLflow's metadata store. Satellite records, prediction results, and experiment metadata are stored here. Other services wait for it to be healthy before starting (healthcheck-guarded).

**`minio`** — Self-hosted S3-compatible object storage. Trained model files, datasets, and MLflow artifacts are stored here. No external cloud dependency.

**`minio-setup`** — One-shot init container that runs right after MinIO starts. Creates the required buckets and sets access policies, then exits.

### MLOps Core

**`mlflow`** — Experiment tracking and model registry. Parameters, metrics, and model versions are logged here during training. Uses PostgreSQL as backend store and MinIO as artifact store.

**`pipeline`** — Orchestrator for data collection and model training. Only runs on demand (`profiles: pipeline`) and exits when done. Supports three modes:
- `collect` — fetch data from Space-Track, NRCan, NOAA, SIDC
- `train` — feature engineering + model training
- `full` — both

Can be triggered by Jenkins with parameters, or run directly from the command line.

### API Services

**`api-dev`** — Development API server. Source code is mounted with hot-reload; changes reflect instantly. Only active in `dev` profile.

**`api-test`** — Test environment API server. Jenkins SSH-es into this container to run test commands (`dev_tests.py`, `test_env_tests.py`, shell scripts). Contains a dedicated system user (`test_user`) for this.

**`api-prod`** — Production API server. Runs behind Nginx, not directly exposed to external traffic. Jenkins deploys here after merge to `main` and manual approval.

### CI/CD

**`gitea`** — Self-hosted Git server. Triggers Jenkins via webhook on every push. Active in `dev` and `test` profiles.

**`jenkins`** — CI/CD automation engine. Runs the relevant test set per branch when a Gitea webhook arrives. Executes the `dev → test → main` auto-merge chain if tests pass. Waits for manual approval before deploying to production. Can also trigger the ML pipeline with parameters.

### Monitoring Stack

**`prometheus`** — Scrapes API, MLflow, and system metrics on a schedule, stores them as time series. Active in `test` and `prod` profiles.

**`grafana`** — Visualizes Prometheus data. Tracks API response times, prediction volumes, Space-Track quota usage, and model metrics.

**`alertmanager`** — Receives alert rules from Prometheus, deduplicates and groups repeated alerts, routes to notification channels.

### Supporting Services

**`scheduler`** — Automated daily report generator that runs at 17:30 (Istanbul time). Queries PostgreSQL for prediction summaries, checks API health, and writes a report to `reports/`. Active only in `prod` profile.

**`nginx`** — Reverse proxy and load balancer. Routes external traffic to `api-prod`. Handles SSL/TLS termination, security headers, and access logs. Active only in `prod` profile.

---

## API

```http
GET /satellite/{norad_id}/risk
```

```json
{
  "satellite_id": "25544",
  "risk_level": "LOW",
  "daily_decay_probability": 0.15,
  "estimated_lifetime_days": 365,
  "confidence_score": 0.87
}
```

---
## Project Layout

<details>
<summary><b>📁 Project Structure</b></summary>

```
src/
├── api/
│   └── endpoints/              # prediction, training, health, monitoring
├── domain/
│   ├── contracts/              # cross-domain schema definitions
│   ├── orbital/
│   │   ├── collection/         # Space-Track API client, strategies, catalog
│   │   │   ├── api_clients/
│   │   │   ├── catalog/
│   │   │   ├── strategies/     # batch + incremental collection
│   │   │   └── validation/
│   │   ├── features/           # feature engineering domain
│   │   │   └── generators/     # angular, physics, spatiotemporal, state vector, targets
│   │   └── processing/         # orbital mechanics
│   │       ├── contracts/
│   │       ├── core/
│   │       ├── engines/        # cleaner, propagation, segmentation, validator
│   │       ├── metrics/
│   │       ├── models/
│   │       ├── repositories/
│   │       └── rust_plugin/    # SGP4 Rust plugin (PyO3 + maturin)
│   ├── timeseries/             # time series generation and storage
│   └── weather/                # space weather data
│       ├── collection/
│       ├── feature_synthesis/  # multi-source merger
│       └── processing/         # solar_flux, geomagnetic_index, sunspot processors
├── machine_learning/
│   ├── data_loader.py
│   ├── satellite_risk_predictor.py
│   ├── predictor2.py
│   ├── feature_engineering/    # survival feature engineer
│   └── models/
│       ├── lstm_neural_network/
│       └── gradient_boosting/
├── monitoring/                 # Prometheus custom metrics
├── notebooks/                  # EDA, calibration studies, space weather analysis
│   ├── calibrations/           # gap, maneuver, rcs, regime, segment studies
│   ├── eda/
│   ├── space_weather/          # solar flux, geomagnetic storms, sunspot analysis
│   └── targets/                # decay rate, physics, regime, segment analysis
├── pipeline/
│   ├── contracts/              # execution lifecycle contracts
│   ├── coordinators/
│   │   ├── phase1_orbital_collection/
│   │   ├── phase2_orbital_processing/
│   │   ├── phase3_orbital_features/
│   │   ├── phase4_environment_collection/
│   │   ├── phase5_environment_processing/
│   │   ├── phase6_environment_synthesis/
│   │   ├── phase7_timeseries_integration/
│   │   └── phase8_model_training/
│   ├── di_containers/          # dependency injection container per phase
│   ├── metadata/               # pipeline run history, dataset metadata
│   ├── monitoring/             # pipeline performance monitor
│   └── orchestration/          # pipeline orchestrator + executor
├── scheduler/                  # daily report generator
└── shared/
    ├── api_compliance/         # quota manager, rate limiting
    ├── checkpoint/             # checkpoint_manager (hash-based skip logic)
    ├── config/                 # config loader, models, interfaces
    ├── enums/
    ├── metadata/               # pipeline metadata store
    ├── policies/               # data freshness policy
    ├── storage/                # S3 adapter (MinIO)
    └── utils/                  # hashing_service, execution_request

infrastructure/
├── config/
│   ├── defaults/               # api, base, catalog, domain, infra, ml, monitoring, pipeline, processing
│   └── environments/           # dev.yml, test.yml, prod.yml
├── database/                   # PostgreSQL schema, init scripts, backup
├── docker/
│   ├── grafana/                # dashboard + datasource provisioning
│   └── images/                 # 7 custom Dockerfiles (api-dev/test/prod, base, jenkins, mlflow, pipeline)
├── monitoring/
│   ├── prometheus/             # Prometheus config + alert rules
│   └── alertmanager/           # alert routing
├── nginx/                      # reverse proxy config, TLS certs
└── jenkins/                    # CasC YAML, plugins list

tests/
├── dev_tests.py
├── test_env_tests.py
├── model_performance_test.py
├── prod_smoke_tests.py
└── test_script_improvements.sh
```

</details>

---

## Tech Stack

**Languages**
- Python — main application language
- Rust — Polars plugin for SGP4 propagator (`orbital_plugin`, PyO3 + maturin)
- SQL — PostgreSQL queries and schema definitions
- Bash / Shell — deployment scripts, CI/CD steps
- Groovy — Jenkinsfile pipeline definition
- YAML — Docker Compose, service and environment configs

**Machine Learning**
- TensorFlow / Keras — Bidirectional LSTM, MultiHeadAttention, Masking, EarlyStopping
- scikit-learn — StandardScaler, train/test split
- NumPy — array operations, sequence building
- MLflow — experiment tracking, model registry, artifact management

**Data Processing**
- Polars — Rust-backed DataFrame library; chosen over pandas for memory efficiency
- Pandas — ML feature tables and DataLoader layer
- SQLAlchemy — PostgreSQL connection and query management
- psycopg2 — PostgreSQL Python driver

**API**
- FastAPI — REST API, async endpoints
- Pydantic — request/response schema validation
- Uvicorn — ASGI server

**Storage**
- PostgreSQL 16 — main database and MLflow backend store
- MinIO — S3-compatible self-hosted object storage (model artifacts, datasets)

**Observability**
- Prometheus — metrics collection and time series storage
- Grafana — dashboards and visualization
- Alertmanager — alert routing and deduplication
- structlog — structured JSON logging

**CI/CD & Platform**
- Docker / Docker Compose — containerization, 15+ services, multi-profile (dev / test / prod)
- Jenkins — CI/CD automation, webhooks, pipeline as code
- Gitea — self-hosted Git server
- Nginx — reverse proxy, SSL/TLS termination
- SSH — Jenkins → container deployment access

**Type Safety**
- mypy — static type analysis
- MonkeyType — runtime type collection, automatic annotation generation
- Python `typing` module — `Optional`, `List`, `Dict`, `Tuple`, `Any`

**Concurrency & Performance**
- `concurrent.futures.ThreadPoolExecutor` — I/O-bound parallel processing (Phase 2, 4, 7)
- `multiprocessing` — GIL bypass for CPU-bound tasks
- PyO3 / maturin — Rust-Python bindings

**External Data Sources**
- Space-Track.org — TLE (Two-Line Element) orbital data
- NRCan (Natural Resources Canada) — F10.7 solar flux
- NOAA — Kp and Ap geomagnetic indices
- SIDC (Royal Observatory of Belgium) — sunspot number

**Orbital Mechanics**
- SGP4 — TLE propagator (GIL-free vectorized via Rust plugin)
- NRLMSISE-00 — atmospheric density model

---

## Challenges

As the project grew, modules started bloating — classes accumulating too many responsibilities, dependencies piling up, and any refactor requiring changes across multiple files at once. Early on I ran into this directly: a few coordinators had become hard to test or extend because they were doing too much.

To avoid it spreading further, I paid deliberate attention to **Single Responsibility Principle (SRP) and modularity** from the early phases onward. Each coordinator delegates to focused components (checkpoint handler, executor, cache handler, error handler) rather than doing everything itself. Feature engineering, orbital mechanics, and data persistence are in separate domain layers rather than mixed into pipeline code. This made the later phases significantly easier to add without breaking existing ones.

The biggest constraint throughout this project was hardware. I'm running everything on a MacBook Air M1 with 8GB RAM. As datasets grew and processing steps got more complex, the system started struggling. The pipeline has 8 phases — each one hit a different bottleneck, and each needed its own fix.

### Phase 1 — Orbital Collection (Space-Track)

Space-Track has a 1000-request-per-day API limit and can be slow. Instead of fetching all satellites at once, I implemented a batch + incremental strategy.

Every phase has a **checkpoint/hash system**. The logic: before a phase runs, it generates a SHA hash from its inputs (manifest files, satellite IDs, date range). If that hash was already recorded, the phase switches to `REUSE` mode and skips entirely — no re-fetching, no re-processing. If the hash is new or inputs changed, it runs in `RUN` mode. Partial failures don't save a checkpoint, so the next run retries from scratch.

**Cold reload** is part of this too: when a service or container restarts, the pipeline resumes from the last valid checkpoint instead of starting at Phase 1. This prevents repeated API calls both during development and in Jenkins-triggered runs.

### Phase 2 — Orbital Processing

Each batch file is loaded, processed, then closed — the full dataset is never in memory at once. Per-satellite processing is parallelized with `ThreadPoolExecutor`; `max_workers` is read from config. I used Polars here: unlike pandas, Polars is Rust-backed and processes the same data with significantly less memory. The difference is very noticeable on large telemetry tables.

### Phase 4 — Environmental Collection (NRCan, NOAA, SIDC)

Solar flux, geomagnetic indices, and sunspot data come from separate HTTP sources. Instead of fetching them sequentially, I run them concurrently with `ThreadPoolExecutor` — all sources start at the same time and don't wait on each other. This is ideal for I/O-bound work and GIL isn't a problem here.

### Phase 7 — Time Series Integration

Instead of a fixed worker count, I calculate it dynamically based on the execution environment:
- `dev`: `max(2, base // 2)` — keeps Docker memory usage under control on M1
- `test`: `max(4, base)`
- `prod`: `min(base * 2, 16)`

Same code, doesn't crash the dev machine, runs at full capacity in prod.

### SGP4 Orbital Propagation

Orbital vector calculations (inside Phase 2) are the most CPU and RAM-intensive part. Instead of the Python SGP4 library, I wrote a **Rust plugin** (`orbital_plugin`) built on top of Polars. `propagate_state_vectors()` runs vectorized without the GIL — the entire segment is processed in one call inside a Polars DataFrame, no Python for-loop. I also used `join_asof` for segment merging — another vectorized Polars operation.

### LSTM Training (Phase 8)

Satellites are loaded one at a time (`load(sat_id)`), never all in RAM at once. Each satellite is capped at the last 365 rows (`df.tail(365)`) — the memory cost of longer history outweighed the model benefit. Instead of full-length padding, I used `Masking(mask_value=-99.0)` — this lets the LSTM learn from irregular timesteps while avoiding the memory overhead of padding every sequence to the maximum length. `batch_size=32` and `EarlyStopping(patience=5)` reduce both training time and memory pressure.

### API Service

Inter-service dependencies (MinIO → MLflow → API) would sometimes cause blocking chains. I added timeout limits to API endpoints and had to manually tune thread pool sizes. For CPU-bound computations I used `multiprocessing` — `threading` doesn't give real parallelism because of the GIL.

### Storage Management — Migrating from MinIO to PostgreSQL

Initially I was writing all intermediate outputs (processed batch files, feature store snapshots, pipeline metadata) to MinIO as S3 objects. But local Docker volumes started filling up. With larger satellite sets, the MinIO container volume would run out of space and crash the pipeline mid-run.

I split the storage strategy in two:
- **MinIO** — kept only for MLflow model artifacts and large datasets (things that genuinely belong in object storage)
- **PostgreSQL** — pipeline metadata, checkpoint records, execution lineage, and recent satellite data moved here

The switch to PostgreSQL also made querying much easier: I can query checkpoint hashes, phase execution history, and recent prediction results with SQL instead of parsing JSON objects stored in MinIO. Volume management became more predictable too — tracking PostgreSQL disk usage in Grafana is straightforward.

---

## What's still in progress

- More advanced LSTM sequence features — current temporal modeling is basic
- Proper model evaluation framework (metrics, validation splits, hyperparameter tuning)
- Distributed processing for larger satellite sets (Spark) — hardware constraint still applies here
- **Risk assessment system overhaul** — current output is a flat CRITICAL / HIGH / MEDIUM / LOW classification; planned to be extended with a more granular scoring approach

---

## Status

Active development. Code is being uploaded gradually — some modules are already here, others will follow over the coming weeks.

---

*Hilal Alpak*
