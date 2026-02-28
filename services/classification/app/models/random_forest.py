"""Random Forest model wrapper."""

from sklearn.ensemble import RandomForestClassifier


def get_model(params=None, use_class_weight: bool = False):
    """Get random forest model with default params."""
    default_params = {
        "n_estimators": 100,
        "max_depth": None,
        "min_samples_split": 2,
        "random_state": 42,
        "n_jobs": -1,
    }
    if use_class_weight:
        default_params["class_weight"] = "balanced"
    if params:
        default_params.update(params)
    return RandomForestClassifier(**default_params)


def get_default_params():
    """Get default hyperparameters."""
    return {
        "n_estimators": 100,
        "max_depth": None,
        "min_samples_split": 2,
        "random_state": 42,
        "n_jobs": -1
    }