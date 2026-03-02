"""SVM model wrapper."""

from sklearn.svm import SVC


def get_model(params=None, use_class_weight: bool = False):
    """Get SVM model with default params."""
    default_params = {
        "kernel": "rbf",
        "C": 1.0,
        "probability": True,
        "random_state": 42,
    }
    if use_class_weight:
        default_params["class_weight"] = "balanced"
    if params:
        default_params.update(params)
    return SVC(**default_params)


def get_default_params():
    """Get default hyperparameters."""
    return {
        "kernel": "rbf",
        "C": 1.0,
    }
