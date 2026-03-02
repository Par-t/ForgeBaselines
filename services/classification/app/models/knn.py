"""KNN model wrapper."""

from sklearn.neighbors import KNeighborsClassifier


def get_model(params=None, use_class_weight: bool = False):
    """Get KNN model with default params."""
    default_params = {
        "n_neighbors": 5,
        "n_jobs": -1,
    }
    if params:
        default_params.update(params)
    return KNeighborsClassifier(**default_params)


def get_default_params():
    """Get default hyperparameters."""
    return {
        "n_neighbors": 5,
    }
