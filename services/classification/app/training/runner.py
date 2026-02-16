"""Training runner for running multiple models."""

import time
import numpy as np
from typing import List, Dict, Any

from app.models.registry import get_model
from app.training.evaluator import evaluate


def run_training(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model_names: List[str],
    experiment_id: str
) -> List[Dict[str, Any]]:
    """Train multiple models and return results.

    Returns list of results, each containing:
    - model_name
    - metrics (accuracy, precision, recall, f1)
    - training_time
    """
    results = []

    for model_name in model_names:
        # Get model
        model = get_model(model_name)

        # Train
        start_time = time.time()
        model.fit(X_train, y_train)
        training_time = time.time() - start_time

        # Evaluate
        metrics = evaluate(model, X_test, y_test)

        # Collect results
        result = {
            "model_name": model_name,
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "confusion_matrix": metrics["confusion_matrix"],
            "training_time": round(training_time, 2)
        }
        results.append(result)

    # Sort by F1 score (descending)
    results.sort(key=lambda x: x["f1"], reverse=True)

    return results