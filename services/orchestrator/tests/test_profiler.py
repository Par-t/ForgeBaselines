"""Unit tests for profile_dataset()."""

import pandas as pd
import numpy as np
import pytest

from app.services.profiler import profile_dataset


@pytest.fixture
def iris_df():
    """30-row Iris-style DataFrame (10 per class, no missing values)."""
    rows = []
    for species in ["Iris-setosa", "Iris-versicolor", "Iris-virginica"]:
        for i in range(10):
            rows.append({
                "Id": len(rows) + 1,
                "SepalLengthCm": 5.0 + i * 0.1,
                "SepalWidthCm": 3.0 + i * 0.05,
                "PetalLengthCm": 1.5 + i * 0.2,
                "PetalWidthCm": 0.2 + i * 0.05,
                "Species": species,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def df_with_missing():
    """Small DataFrame with NaN values in known positions."""
    return pd.DataFrame({
        "a": [1.0, np.nan, 3.0, np.nan],
        "b": ["x", "y", np.nan, "z"],
        "c": [10, 20, 30, 40],
    })


def test_n_rows_n_cols(iris_df):
    profile = profile_dataset(iris_df)
    assert profile["n_rows"] == 30
    assert profile["n_cols"] == 6


def test_column_names(iris_df):
    profile = profile_dataset(iris_df)
    assert profile["column_names"] == iris_df.columns.tolist()


def test_column_types(iris_df):
    profile = profile_dataset(iris_df)
    assert "Id" in profile["column_types"]
    assert profile["column_types"]["Species"] == "object"
    assert profile["column_types"]["SepalLengthCm"] in ("float64", "float32")


def test_numeric_categorical_counts(iris_df):
    profile = profile_dataset(iris_df)
    # Id, SepalLengthCm, SepalWidthCm, PetalLengthCm, PetalWidthCm = 5 numeric
    # Species = 1 categorical
    assert profile["numeric_cols"] == 5
    assert profile["categorical_cols"] == 1


def test_missing_values_none(iris_df):
    profile = profile_dataset(iris_df)
    assert profile["missing_values"] == 0
    assert all(v == 0 for v in profile["missing_by_column"].values())


def test_missing_values_with_nans(df_with_missing):
    profile = profile_dataset(df_with_missing)
    assert profile["missing_values"] == 3  # 2 in "a" + 1 in "b"
    assert profile["missing_by_column"]["a"] == 2
    assert profile["missing_by_column"]["b"] == 1
    assert profile["missing_by_column"]["c"] == 0


def test_cardinality(iris_df):
    profile = profile_dataset(iris_df)
    assert profile["cardinality"]["Species"] == 3
    assert profile["cardinality"]["Id"] == 30  # all unique


def test_cardinality_constant_column():
    df = pd.DataFrame({"x": [7, 7, 7, 7], "y": [1, 2, 3, 4]})
    profile = profile_dataset(df)
    assert profile["cardinality"]["x"] == 1
    assert profile["cardinality"]["y"] == 4


def test_memory_mb_positive(iris_df):
    profile = profile_dataset(iris_df)
    assert profile["memory_mb"] > 0
