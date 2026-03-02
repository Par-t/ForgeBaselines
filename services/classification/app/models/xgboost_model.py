"""XGBoost model wrapper."""

from xgboost import XGBClassifier


def get_model(params=None, use_class_weight: bool = False):
    """Get XGBoost model with default params."""
    default_params = {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "eval_metric": "logloss",
        "random_state": 42,
        "verbosity": 0,
    }
    if params:
        default_params.update(params)
    return XGBClassifier(**default_params)


def get_default_params():
    """Get default hyperparameters."""
    return {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
    }
