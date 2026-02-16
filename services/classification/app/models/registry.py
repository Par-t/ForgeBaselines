"""Model registry for managing available models."""

from app.models import logistic, random_forest, gradient_boosting


MODEL_REGISTRY = {
    "logistic_regression": logistic,
    "random_forest": random_forest,
    "gradient_boosting": gradient_boosting,
}


def get_model(model_name: str, params=None):
    """Get a model by name with optional params."""
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(MODEL_REGISTRY.keys())}")

    model_module = MODEL_REGISTRY[model_name]
    return model_module.get_model(params)


def get_available_models():
    """Get list of available model names."""
    return list(MODEL_REGISTRY.keys())