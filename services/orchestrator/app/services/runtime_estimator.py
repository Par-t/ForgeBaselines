"""Runtime estimation service."""

import math
from typing import Dict, List, Any


# Model complexity weights
MODEL_WEIGHTS = {
    "logistic_regression": 1.0,
    "random_forest": 3.0,
    "gradient_boosting": 4.0,
}


def estimate_runtime(profile: Dict[str, Any], model_names: List[str]) -> Dict[str, Any]:
    """Estimate training runtime based on dataset profile and models.

    Formula: C = log2(n_samples) * n_features * (1 + missing_ratio) * model_weight

    Runtime bands:
    - low (C < 100): "< 1 min"
    - medium (100 <= C < 500): "1-5 min"
    - high (C >= 500): "5-15 min"
    """
    n_rows = profile["n_rows"]
    n_cols = profile["n_cols"]
    missing_values = profile["missing_values"]
    total_cells = n_rows * n_cols
    missing_ratio = missing_values / total_cells if total_cells > 0 else 0

    # Calculate complexity for each model
    estimates = {}
    max_complexity = 0

    for model_name in model_names:
        weight = MODEL_WEIGHTS.get(model_name, 1.0)
        complexity = math.log2(max(n_rows, 2)) * n_cols * (1 + missing_ratio) * weight
        band = _get_runtime_band(complexity)

        estimates[model_name] = {
            "complexity_score": round(complexity, 2),
            "estimated_runtime": band
        }
        max_complexity = max(max_complexity, complexity)

    # Overall estimate is based on max complexity (sequential training)
    overall_band = _get_runtime_band(max_complexity)

    return {
        "overall_estimate": overall_band,
        "per_model": estimates,
        "complexity_factors": {
            "n_rows": n_rows,
            "n_cols": n_cols,
            "missing_ratio": round(missing_ratio, 3)
        }
    }


def _get_runtime_band(complexity: float) -> str:
    """Map complexity score to runtime band."""
    if complexity < 100:
        return "< 1 min"
    elif complexity < 500:
        return "1-5 min"
    else:
        return "5-15 min"
