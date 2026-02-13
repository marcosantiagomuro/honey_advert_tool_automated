# Honey Advert Tool

Automated Multi-Platform Publishing Orchestration Framework

---

## Overview

The Honey Advert Tool is a modular automation framework designed to coordinate content publication across multiple online platforms.

It provides:

- A centralized orchestration layer
- Deterministic execution scheduling
- Pluggable publisher adapters
- Structured logging and state persistence
- CI/CD-based execution via GitHub Actions

The system is built using Python and is designed to be extensible, reproducible, and automation-friendly.

---

## Architecture

The framework follows a layered orchestration model:

GitHub Actions Workflow  
        ↓  
automation_runner.py (Orchestrator)  
        ↓  
publishers.py (Dispatcher)  
        ↓  
Publisher Scripts (Platform Adapters)  
        ↓  
External Platform APIs  

### Core Components

#### 1. Orchestrator (`automation_runner.py`)

The orchestrator coordinates the overall execution process. It is responsible for:

- Loading configuration and input data
- Managing persistent execution state
- Deterministic round-robin assignment logic
- Executing publisher adapters
- Recording structured execution logs

The orchestrator ensures that each execution cycle is reproducible and auditable.

---

#### 2. Publisher Dispatcher (`publishers.py`)

The dispatcher maps logical publisher labels to concrete script implementations.

Responsibilities include:

- Maintaining a registry of available publisher adapters
- Injecting runtime configuration into subprocesses
- Executing publisher scripts
- Capturing stdout/stderr and exit codes

This layer isolates orchestration logic from platform-specific publishing code.

---

#### 3. Publisher Scripts (`publisher_scripts/`)

Each publisher adapter:

- Reads required API credentials from environment variables
- Generates publishable content using shared utilities
- Submits content via the platform’s API
- Returns structured execution output

Adapters are independent and can be added or removed without modifying the core orchestrator.

---

#### 4. Shared Utilities (`utils.py`)

Shared helper functions provide:

- Environment validation
- Content generation utilities
- Runtime context handling
- Deterministic run index derivation

This ensures consistent behaviour across all publisher adapters.

---

#### 5. Persistent State and Logging

The system maintains execution artefacts in repository-managed files:

| File | Purpose |
|------|---------|
| `credentials.csv` | Input pool for assignment logic |
| `csv_credentials_state.json` | Persistent mapping and rotation state |
| `submissions.csv` | Append-only execution log |

These files allow reproducible scheduling, deterministic assignment, and longitudinal analysis across multiple runs.

---

## Execution via GitHub Actions

The tool is designed to run automatically using GitHub Actions.

Workflow file:

```
.github/workflows/run-publishers-all.yml
```

### Supported Triggers

- Scheduled execution (cron)
- Manual workflow dispatch

Example schedule:

```yaml
on:
  schedule:
    - cron: '0 6,18 * * *'
```

This configuration runs the automation twice daily (UTC).

---

## Secrets and Configuration

Sensitive values such as API tokens are stored securely as GitHub Actions Secrets.

At runtime:

- Secrets are injected into the job environment
- A `.env` file may be generated dynamically
- Publisher scripts access credentials via environment variables

No secrets are committed to the repository.

---

## Deterministic Rotation Logic

When executed inside GitHub Actions, the system derives a run index from:

```
GITHUB_RUN_NUMBER
```

Selection logic follows a deterministic round-robin model:

```
index = run_index mod k
```

This ensures:

- Even distribution
- Predictable assignment
- Reproducibility across runs

---

## Repository Structure

```
.
├── automation_runner.py
├── publishers.py
├── utils.py
├── publisher_scripts/
│   ├── github_gist_1.py
│   ├── gitlab_snippet_1.py
│   ├── pastebin_post_1.py
│   └── ...
├── credentials.csv
├── csv_credentials_state.json
├── submissions.csv
├── requirements.txt
└── .github/workflows/run-publishers-all.yml
```

---

## Usage

To execute:

1. Configure required secrets in the repository settings
2. Ensure required CSV file exist
3. Enable GitHub Actions
4. Trigger manually or wait for scheduled run

Execution results will be written to the log file and optionally committed back to the repository.

---

## Extending the Framework

To add a new publishing target:

1. Create a new script inside `publisher_scripts/`
2. Register it in `publishers.py` under `SCRIPTS`
3. Provide required environment variables via GitHub Secrets
4. Commit and push

No changes to the core orchestrator are required.

---

## Disclaimer

This framework is provided for automation and research purposes. Users are responsible for complying with platform policies and applicable laws when deploying automated publishing systems.
