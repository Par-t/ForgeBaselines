"""Gradient Boosting model wrapper."""

from sklearn.ensemble import GradientBoostingClassifier


def get_model(params=None):
    """Get gradient boosting model with default params."""
    default_params = {
        "n_estimators": 100,
        "learning_rate": 0.1,
        "max_depth": 3,
        "random_state": 42
    }
    if params:
        default_params.update(params)
    return GradientBoostingClassifier(**default_params)


def get_default_params():
    """Get default hyperparameters."""
    return {
        "n_estimators": 100,
        "learning_rate": 0.1,
        "max_depth": 3,
        "random_state": 42
    }