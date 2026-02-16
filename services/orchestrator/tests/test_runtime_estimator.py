"""Test runtime estimation."""

import pytest
from app.services.runtime_estimator import estimate_runtime


def test_estimate_small_dataset():
    """Test runtime estimation for small dataset (Iris-like)."""
    profile = {
        "n_rows": 150,
        "n_cols": 5,
        "missing_values": 0
    }
    model_names = ["logistic_regression", "random_forest", "gradient_boosting"]

    result = estimate_runtime(profile, model_names)

    # Iris with GB is medium complexity (~145)
    assert result["overall_estimate"] == "1-5 min"
    assert "logistic_regression" in result["per_model"]
    assert "random_forest" in result["per_model"]
    assert "gradient_boosting" in result["per_model"]
    assert result["complexity_factors"]["missing_ratio"] == 0


def test_estimate_medium_dataset():
    """Test runtime estimation for medium dataset."""
    profile = {
        "n_rows": 10000,
        "n_cols": 50,
        "missing_values": 5000
    }
    model_names = ["random_forest"]

    result = estimate_runtime(profile, model_names)

    # 10k rows, 50 cols, random forest -> should be medium
    assert result["overall_estimate"] in ["1-5 min", "5-15 min"]
    assert result["complexity_factors"]["missing_ratio"] > 0


def test_estimate_large_dataset():
    """Test runtime estimation for large dataset."""
    profile = {
        "n_rows": 100000,
        "n_cols": 100,
        "missing_values": 0
    }
    model_names = ["gradient_boosting"]

    result = estimate_runtime(profile, model_names)

    # 100k rows, 100 cols, gradient boosting -> should be high
    assert result["overall_estimate"] == "5-15 min"


def test_estimate_edge_case_single_row():
    """Test runtime estimation with minimal dataset."""
    profile = {
        "n_rows": 1,
        "n_cols": 1,
        "missing_values": 0
    }
    model_names = ["logistic_regression"]

    result = estimate_runtime(profile, model_names)

    # Should not crash with edge case
    assert "overall_estimate" in result
    assert result["overall_estimate"] == "< 1 min"


def test_estimate_multiple_models_max_complexity():
    """Test that overall estimate uses max complexity across models."""
    profile = {
        "n_rows": 5000,
        "n_cols": 20,
        "missing_values": 0
    }
    # Mix of cheap and expensive models
    model_names = ["logistic_regression", "gradient_boosting"]

    result = estimate_runtime(profile, model_names)

    # Overall should be based on the most expensive model (gradient_boosting)
    gb_complexity = result["per_model"]["gradient_boosting"]["complexity_score"]
    lr_complexity = result["per_model"]["logistic_regression"]["complexity_score"]

    assert gb_complexity > lr_complexity  # GB is more complex
