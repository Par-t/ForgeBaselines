"""Model evaluation utilities."""

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)
from typing import Dict, Any


def evaluate(model, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
    """Evaluate a trained model on test data.

    Returns metrics: accuracy, precision, recall, f1, confusion_matrix.
    Handles both binary and multiclass classification.
    """
    y_pred = model.predict(X_test)

    # Determine if binary or multiclass
    n_classes = len(np.unique(y_test))
    average = "binary" if n_classes == 2 else "weighted"

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, average=average, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, average=average, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, average=average, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist()
    }

    return metrics