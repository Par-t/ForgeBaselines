"""Test training runner."""

import numpy as np
from sklearn.datasets import load_iris
from app.training.runner import run_training


def test_run_training_single_model():
    """Test training runner with single model."""
    # Load Iris
    X, y = load_iris(return_X_y=True)
    X_train, X_test = X[:120], X[120:]
    y_train, y_test = y[:120], y[120:]

    # Run training
    results = run_training(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        model_names=["logistic_regression"],
        experiment_id="test-exp-1"
    )

    # Verify results
    assert len(results) == 1
    result = results[0]
    assert result["model_name"] == "logistic_regression"
    assert result["accuracy"] > 0.8
    assert result["f1"] > 0.8
    assert result["training_time"] >= 0  # Can be 0 for tiny datasets
    assert "confusion_matrix" in result


def test_run_training_multiple_models():
    """Test training runner with multiple models."""
    X, y = load_iris(return_X_y=True)
    X_train, X_test = X[:120], X[120:]
    y_train, y_test = y[:120], y[120:]

    # Run training with all models
    results = run_training(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        model_names=["logistic_regression", "random_forest", "gradient_boosting"],
        experiment_id="test-exp-2"
    )

    # Verify results
    assert len(results) == 3

    # Check all models present
    model_names = [r["model_name"] for r in results]
    assert "logistic_regression" in model_names
    assert "random_forest" in model_names
    assert "gradient_boosting" in model_names

    # Check all have decent metrics (0.7 threshold for simple split)
    for result in results:
        assert result["accuracy"] > 0.7, f"{result['model_name']} accuracy too low"
        assert result["f1"] > 0.7, f"{result['model_name']} F1 too low"


def test_results_sorted_by_f1():
    """Test that results are sorted by F1 score (descending)."""
    X, y = load_iris(return_X_y=True)
    X_train, X_test = X[:120], X[120:]
    y_train, y_test = y[:120], y[120:]

    results = run_training(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        model_names=["logistic_regression", "random_forest", "gradient_boosting"],
        experiment_id="test-exp-3"
    )

    # Check sorting
    f1_scores = [r["f1"] for r in results]
    assert f1_scores == sorted(f1_scores, reverse=True), "Results not sorted by F1"