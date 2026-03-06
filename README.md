# ForgeBaselines

Dockerized ML orchestration platform for generating reproducible baselines on tabular
classification and information retrieval tasks. Upload a CSV, configure your experiment,
get a ranked leaderboard.

> Built with FastAPI · scikit-learn · BM25 · MLflow · Next.js · Docker

---

## Architecture

```
  User ───────────▶ Frontend (Next.js) — localhost:3000
                         │ API calls
                         ▼
                    Orchestrator (FastAPI, 8000)
                    ├──▶ Classification (FastAPI, 8001)
                    ├──▶ IR / BM25 (FastAPI, 8002)
                    └──▶ MLflow (5001)
```

All services run locally via Docker Compose. There is no cloud deployment at this time.

| Service        | Port | Role                                                        |
|----------------|------|-------------------------------------------------------------|
| frontend       | 3000 | Next.js UI — upload, configure, progress, results          |
| orchestrator   | 8000 | Main API — routing, preprocessing, experiment orchestration |
| classification | 8001 | Internal — model training + MLflow logging                  |
| ir             | 8002 | Internal — BM25 retrieval + metrics + MLflow logging        |
| mlflow         | 5001 | Experiment tracking UI + REST API                           |

Data is stored locally under `./data/` (Docker volume mount). MLflow artifacts are stored
locally under `./mlflow-artifacts/`.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

## Local Setup

```bash
git clone https://github.com/Parth-Agarwal216/ForgeBaselines.git
cd ForgeBaselines
cp .env.example .env
docker compose up --build   # first build ~3-5 min
```

| URL                        | What                       |
|----------------------------|----------------------------|
| http://localhost:3000      | Main UI                    |
| http://localhost:8000/docs | Orchestrator API (Swagger) |
| http://localhost:5001      | MLflow experiment tracker  |

---

## Usage

### Classification

1. **Upload** — drop a CSV at `/upload`
2. **Configure** — pick target column, review auto-detected column roles, select models, set preprocessing options
3. **Run** — trains selected models (Logistic Regression, Random Forest, Gradient Boosting, XGBoost, SVM, KNN)
4. **Results** — live progress bar while training, leaderboard ranked by F1 on completion, download as CSV

### Information Retrieval

1. **Upload** — upload a corpus CSV and a queries CSV from the dashboard
2. **Configure** — select corpus/query datasets and map text columns
3. **Run** — builds a BM25 index and scores all queries
4. **Results** — live progress bar during scoring, MAP / nDCG@10 / Recall / MRR metrics on completion

Both experiment types run asynchronously — the POST returns immediately and the results page
polls `/status` until completion.

---

## Seed Data

```bash
pip install pandas scikit-learn requests   # one-time, host machine
python scripts/seed_test_data.py
```

Uploads three sample datasets (Iris, Wine, Titanic) so you can test the full pipeline immediately.

---

## Tests

```bash
docker compose exec orchestrator pytest tests/ -v --tb=short
docker compose exec classification pytest tests/ -v --tb=short
```

---

## CI

Every push to `main` triggers GitHub Actions CI: pytest for both backend services + `npm run build` for the frontend (3 parallel jobs).

---

## Development

Hot reload is on for orchestrator and frontend. The IR service requires a rebuild after code changes:

```bash
docker compose up -d --build ir
```

Other useful commands:

```bash
docker compose logs -f orchestrator    # tail a service
docker compose up --build frontend     # rebuild after dep changes
docker compose down                    # stop everything
```

---

## Auth

Sign in with a magic link (passwordless). Enter your email → click the link → you're in.
Each user's datasets and experiments are fully isolated.
