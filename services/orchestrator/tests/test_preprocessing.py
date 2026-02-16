"""Test preprocessing pipeline."""

import pandas as pd
import numpy as np
import pytest
from app.preprocessing.pipeline import preprocess_dataset


def test_preprocess_iris():
    """Test preprocessing on Iris dataset."""
    # Load Iris dataset
    df = pd.read_csv("/app/data/data_dev/Iris.csv")

    # Preprocess
    X_train, X_test, y_train, y_test, preprocessor = preprocess_dataset(
        df, target_column="Species", test_size=0.2
    )

    # Verify shapes
    assert X_train.shape[0] == 120  # 80% of 150
    assert X_test.shape[0] == 30    # 20% of 150
    assert y_train.shape[0] == 120
    assert y_test.shape[0] == 30

    # Verify no NaN values
    assert not np.isnan(X_train).any()
    assert not np.isnan(X_test).any()

    # Verify preprocessor is fitted
    assert preprocessor is not None


def test_preprocess_with_missing_values():
    """Test preprocessing handles missing values."""
    df = pd.DataFrame({
        'num1': [1.0, 2.0, np.nan, 4.0, 5.0],
        'num2': [10, 20, 30, np.nan, 50],
        'cat1': ['A', 'B', None, 'A', 'B'],
        'target': [0, 1, 0, 1, 0]
    })

    X_train, X_test, y_train, y_test, preprocessor = preprocess_dataset(
        df, target_column="target", test_size=0.4
    )

    # Verify no NaN in output
    assert not np.isnan(X_train).any()
    assert not np.isnan(X_test).any()


def test_preprocess_mixed_types():
    """Test preprocessing with mixed numeric and categorical columns."""
    df = pd.DataFrame({
        'age': [25, 30, 35, 40, 45, 50],
        'income': [50000, 60000, 70000, 80000, 90000, 100000],
        'city': ['NYC', 'LA', 'NYC', 'SF', 'LA', 'SF'],
        'bought': [0, 1, 0, 1, 1, 0]
    })

    X_train, X_test, y_train, y_test, preprocessor = preprocess_dataset(
        df, target_column="bought", test_size=0.33
    )

    # Should have encoded categorical + scaled numeric
    assert X_train.shape[1] > 2  # More columns due to one-hot encoding
    assert not np.isnan(X_train).any()
