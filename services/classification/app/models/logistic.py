"""Logistic Regression model wrapper."""

from sklearn.linear_model import LogisticRegression


def get_model(params=None):
    """Get logistic regression model with default params."""
    default_params = {
        "max_iter": 1000,
        "random_state": 42,
        "solver": "lbfgs"
    }
    if params:
        default_params.update(params)
    return LogisticRegression(**default_params)


def get_default_params():
    """Get default hyperparameters."""
    return {
        "max_iter": 1000,
        "random_state": 42,
        "solver": "lbfgs"
    }
