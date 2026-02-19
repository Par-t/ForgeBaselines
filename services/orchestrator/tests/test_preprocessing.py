"""Test preprocessing pipeline."""

import pandas as pd
import numpy as np
import pytest
from app.preprocessing.pipeline import preprocess_dataset


def test_preprocess_iris():
    """Test preprocessing on Iris dataset."""
    df = pd.read_csv("/app/data/data_dev/Iris.csv")

    X_train, X_test, y_train, y_test, preprocessor, label_classes = preprocess_dataset(
        df, target_column="Species", test_size=0.2
    )

    assert X_train.shape[0] == 120
    assert X_test.shape[0] == 30
    assert y_train.shape[0] == 120
    assert y_test.shape[0] == 30

    # Labels are integers now, not strings
    assert y_train.dtype in [np.int32, np.int64]
    assert not np.isnan(X_train).any()
    assert not np.isnan(X_test).any()

    # Label mapping is preserved
    assert len(label_classes) == 3
    assert "Iris-setosa" in label_classes


def test_preprocess_with_missing_values():
    """Test preprocessing handles missing values."""
    df = pd.DataFrame({
        'num1': [1.0, 2.0, np.nan, 4.0, 5.0],
        'num2': [10, 20, 30, np.nan, 50],
        'cat1': ['A', 'B', None, 'A', 'B'],
        'target': [0, 1, 0, 1, 0]
    })

    X_train, X_test, y_train, y_test, preprocessor, label_classes = preprocess_dataset(
        df, target_column="target", test_size=0.4
    )

    assert not np.isnan(X_train).any()
    assert not np.isnan(X_test).any()
    assert len(label_classes) == 2  # 0 and 1


def test_preprocess_mixed_types():
    """Test preprocessing with mixed numeric and categorical columns."""
    df = pd.DataFrame({
        'age': [25, 30, 35, 40, 45, 50],
        'income': [50000, 60000, 70000, 80000, 90000, 100000],
        'city': ['NYC', 'LA', 'NYC', 'SF', 'LA', 'SF'],
        'bought': [0, 1, 0, 1, 1, 0]
    })

    X_train, X_test, y_train, y_test, preprocessor, label_classes = preprocess_dataset(
        df, target_column="bought", test_size=0.33
    )

    assert X_train.shape[1] > 2  # More columns due to one-hot encoding
    assert not np.isnan(X_train).any()
    assert len(label_classes) == 2
