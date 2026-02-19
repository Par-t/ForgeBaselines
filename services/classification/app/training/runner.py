"""Training runner for running multiple models."""

import time
import os
import numpy as np
from typing import List, Dict, Any
import mlflow

from app.models.registry import get_model, get_available_models
from app.training.evaluator import evaluate


def run_training(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model_names: List[str],
    experiment_id: str,
    label_classes: List[str] = None
) -> List[Dict[str, Any]]:
    """Train multiple models and return results with MLflow logging.

    Returns list of results, each containing:
    - model_name
    - metrics (accuracy, precision, recall, f1)
    - training_time
    """
    # Set MLflow tracking URI
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    mlflow.set_tracking_uri(mlflow_uri)

    # Set experiment (create if doesn't exist)
    mlflow.set_experiment(experiment_id)

    results = []

    for model_name in model_names:
        # Start MLflow run
        with mlflow.start_run(run_name=model_name):
            # Get model
            model = get_model(model_name)

            # Log model parameters
            mlflow.log_param("model_name", model_name)
            mlflow.log_param("n_train_samples", len(X_train))
            mlflow.log_param("n_test_samples", len(X_test))
            mlflow.log_param("n_features", X_train.shape[1])
            if label_classes:
                mlflow.log_param("label_classes", ",".join(label_classes))

            # Train
            start_time = time.time()
            model.fit(X_train, y_train)
            training_time = time.time() - start_time

            # Evaluate
            metrics = evaluate(model, X_test, y_test)

            # Log metrics to MLflow
            mlflow.log_metric("accuracy", metrics["accuracy"])
            mlflow.log_metric("precision", metrics["precision"])
            mlflow.log_metric("recall", metrics["recall"])
            mlflow.log_metric("f1", metrics["f1"])
            mlflow.log_metric("training_time", round(training_time, 2))

            # Log model artifact
            mlflow.sklearn.log_model(model, "model")

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