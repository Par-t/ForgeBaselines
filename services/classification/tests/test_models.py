"""Test individual model wrappers."""

import numpy as np
from sklearn.datasets import load_iris
from app.models.registry import get_model, get_available_models


def test_model_registry():
    """Test that model registry returns all expected models."""
    models = get_available_models()
    assert "logistic_regression" in models
    assert "random_forest" in models
    assert "gradient_boosting" in models
    assert len(models) == 3


def test_logistic_regression():
    """Test logistic regression model trains and predicts."""
    # Load Iris
    X, y = load_iris(return_X_y=True)
    X_train, X_test = X[:120], X[120:]
    y_train, y_test = y[:120], y[120:]

    # Get model and train
    model = get_model("logistic_regression")
    model.fit(X_train, y_train)

    # Predict and check accuracy (threshold 0.7 for simple split)
    accuracy = model.score(X_test, y_test)
    assert accuracy > 0.7, f"Logistic regression accuracy too low: {accuracy}"


def test_random_forest():
    """Test random forest model trains and predicts."""
    X, y = load_iris(return_X_y=True)
    X_train, X_test = X[:120], X[120:]
    y_train, y_test = y[:120], y[120:]

    model = get_model("random_forest")
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    assert accuracy > 0.7, f"Random forest accuracy too low: {accuracy}"


def test_gradient_boosting():
    """Test gradient boosting model trains and predicts."""
    X, y = load_iris(return_X_y=True)
    X_train, X_test = X[:120], X[120:]
    y_train, y_test = y[:120], y[120:]

    model = get_model("gradient_boosting")
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    assert accuracy > 0.7, f"Gradient boosting accuracy too low: {accuracy}"


def test_unknown_model():
    """Test that unknown model raises error."""
    try:
        get_model("unknown_model")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown model" in str(e)
