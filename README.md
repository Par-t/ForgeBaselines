# ForgeBaselines

Dockerized ML orchestration platform for generating reproducible baselines on tabular
classification tasks. Upload a CSV, configure your experiment, get a ranked leaderboard.

> Built with FastAPI · scikit-learn · MLflow · Next.js · Docker

---

## Architecture

Four services on a shared Docker network:

| Service        | Port | Role                                                   |
|----------------|------|--------------------------------------------------------|
| orchestrator   | 8000 | Main API — upload, profiling, experiment orchestration |
| classification | 8001 | Internal — model training + MLflow logging             |
| mlflow         | 5001 | Experiment tracking UI + REST API                      |
| frontend       | 3000 | Next.js UI — upload → configure → results              |

Frontend calls orchestrator only. Orchestrator calls classification and MLflow
internally. Classification never receives direct external traffic.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

## Local Setup

```bash
git clone <repo-url>
cd ForgeBaselines
cp .env.example .env        # defaults work out of the box
docker-compose up --build   # first build ~3-5 min
```

| URL                        | What                       |
|----------------------------|----------------------------|
| http://localhost:3000      | Main UI                    |
| http://localhost:8000/docs | Orchestrator API (Swagger) |
| http://localhost:5001      | MLflow experiment tracker  |

---

## Usage

1. **Upload** — drop a CSV at `/upload`
2. **Configure** — pick target column, review auto-detected column roles, select models
3. **Run** — trains Logistic Regression, Random Forest, and Gradient Boosting
4. **Results** — leaderboard ranked by F1 with per-model metrics

---

## Tests

```bash
docker-compose exec orchestrator pytest tests/ -v --tb=short
docker-compose exec classification pytest tests/ -v --tb=short
```

---

## Development

Hot reload is on for all services. Edit Python files under `services/*/app/` or
frontend files under `services/frontend/app/` — changes reflect immediately.

```bash
docker-compose logs -f orchestrator    # tail a service
docker-compose up --build frontend     # rebuild after dep changes
docker-compose down                    # stop everything
```

---

## Roadmap

- **V1.1** S3 storage · EC2 deployment · CI/CD
- **V1.2** Firebase auth · per-user isolation
- **V2**   Conversational agent (LangGraph + GPT-4o) with chain-of-thought planning
