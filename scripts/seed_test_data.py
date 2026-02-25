#!/usr/bin/env python3
"""Seed the orchestrator with sample datasets for testing.

Usage:
    # With services running (docker compose up):
    python scripts/seed_test_data.py

    # Against a remote host:
    python scripts/seed_test_data.py --base-url http://forgebaselines.mooo.com/api
"""

import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests
from sklearn.datasets import load_iris, load_wine


DATASETS = {
    "iris": {
        "loader": lambda: _load_sklearn("iris"),
        "description": "150 rows, 3 classes, 4 numeric features",
    },
    "wine": {
        "loader": lambda: _load_sklearn("wine"),
        "description": "178 rows, 3 classes, 13 numeric features",
    },
    "titanic": {
        "loader": lambda: _make_titanic(),
        "description": "891 rows, 2 classes, mixed numeric + categorical",
    },
}


def _load_sklearn(name: str) -> pd.DataFrame:
    """Load an sklearn toy dataset as a DataFrame with a string target."""
    if name == "iris":
        bunch = load_iris(as_frame=True)
        df = bunch.frame.rename(columns={"target": "Species"})
        df["Species"] = df["Species"].map(
            {0: "setosa", 1: "versicolor", 2: "virginica"}
        )
    elif name == "wine":
        bunch = load_wine(as_frame=True)
        df = bunch.frame.rename(columns={"target": "class"})
        df["class"] = df["class"].map({0: "class_0", 1: "class_1", 2: "class_2"})
    else:
        raise ValueError(f"Unknown sklearn dataset: {name}")
    return df


def _make_titanic() -> pd.DataFrame:
    """Build a simplified Titanic-style dataset (no external download needed).

    Features mirror the classic Kaggle Titanic columns so the preprocessing
    pipeline exercises both numeric imputation and categorical encoding.
    """
    import numpy as np

    rng = np.random.RandomState(42)
    n = 891

    pclass = rng.choice([1, 2, 3], size=n, p=[0.24, 0.21, 0.55])
    sex = rng.choice(["male", "female"], size=n, p=[0.65, 0.35])
    age = rng.normal(30, 12, size=n).clip(1, 80).round(1)
    sibsp = rng.choice([0, 1, 2, 3, 4], size=n, p=[0.68, 0.23, 0.05, 0.02, 0.02])
    parch = rng.choice([0, 1, 2, 3], size=n, p=[0.76, 0.13, 0.09, 0.02])
    fare = (pclass * -15 + 60 + rng.exponential(10, size=n)).round(2)
    embarked = rng.choice(["S", "C", "Q"], size=n, p=[0.72, 0.19, 0.09])

    # Survival roughly correlated with sex + class
    base_prob = 0.38
    prob = base_prob + (sex == "female") * 0.35 - (pclass == 3) * 0.15
    survived = (rng.random(n) < prob).astype(int)

    # Sprinkle missing values (like the real dataset)
    age_mask = rng.random(n) < 0.20
    age = age.astype(object)
    age[age_mask] = None

    embarked_mask = rng.random(n) < 0.02
    embarked = embarked.astype(object)
    embarked[embarked_mask] = None

    return pd.DataFrame(
        {
            "Pclass": pclass,
            "Sex": sex,
            "Age": age,
            "SibSp": sibsp,
            "Parch": parch,
            "Fare": fare,
            "Embarked": embarked,
            "Survived": survived,
        }
    )


def upload_csv(base_url: str, name: str, df: pd.DataFrame) -> dict:
    """Upload a DataFrame as a CSV file to the orchestrator."""
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    resp = requests.post(
        f"{base_url}/datasets/upload",
        files={"file": (f"{name}.csv", buf, "text/csv")},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Seed ForgeBaselines with sample datasets")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Orchestrator base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--datasets",
        nargs="*",
        choices=list(DATASETS.keys()),
        default=list(DATASETS.keys()),
        help="Which datasets to upload (default: all)",
    )
    args = parser.parse_args()

    print(f"Seeding datasets to {args.base_url}\n")

    for name in args.datasets:
        info = DATASETS[name]
        print(f"  {name}: {info['description']}")
        try:
            df = info["loader"]()
            result = upload_csv(args.base_url, name, df)
            print(f"    -> uploaded  dataset_id={result['dataset_id']}  "
                  f"rows={result['rows']}  cols={result['cols']}\n")
        except requests.ConnectionError:
            print(f"    -> FAILED: cannot connect to {args.base_url}")
            print("       Is the orchestrator running? (docker compose up)")
            sys.exit(1)
        except Exception as e:
            print(f"    -> FAILED: {e}\n")

    print("Done.")


if __name__ == "__main__":
    main()