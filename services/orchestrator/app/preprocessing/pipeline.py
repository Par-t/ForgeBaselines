"""Preprocessing pipeline."""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from typing import Tuple, Any, List, Optional

from app.schemas.plan import ColumnConfig


def preprocess_dataset(
    df: pd.DataFrame,
    target_column: str,
    test_size: float = 0.2,
    column_config: Optional[ColumnConfig] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Any, List[str]]:
    """Preprocess dataset: impute, encode, scale, split.

    Returns X_train, X_test, y_train, y_test (as integers), preprocessor, label_classes.
    label_classes maps integer index → original class name (e.g. ["Iris-setosa", ...]).

    column_config: optional ColumnConfig specifying columns to drop (ignore_columns)
    and/or an explicit feature allowlist (feature_columns). When None, all non-target
    columns are used as features (V1 default behaviour).
    """
    working_df = df.copy()
    if column_config is not None:
        cols_to_drop = [c for c in column_config.ignore_columns if c in working_df.columns]
        if cols_to_drop:
            working_df = working_df.drop(columns=cols_to_drop)
        if column_config.feature_columns:
            keep = set(column_config.feature_columns) | {target_column}
            working_df = working_df[[c for c in working_df.columns if c in keep]]

    X = working_df.drop(columns=[target_column])
    y = working_df[target_column]

    # Encode target labels → integers, preserve class mapping
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    label_classes = le.classes_.tolist()  # e.g. ["Iris-setosa", "Iris-versicolor", "Iris-virginica"]

    # Identify column types
    numeric_cols = X.select_dtypes(include=['int64', 'float64']).columns.tolist()
    categorical_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()

    # Build transformers
    num_pipeline = Pipeline([
        ('impute', SimpleImputer(strategy='median')),
        ('scale', StandardScaler())
    ])

    cat_pipeline = Pipeline([
        ('impute', SimpleImputer(strategy='most_frequent')),
        ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    preprocessor = ColumnTransformer([
        ('num', num_pipeline, numeric_cols),
        ('cat', cat_pipeline, categorical_cols)
    ])

    # Split (stratify on encoded labels)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=test_size, random_state=42, stratify=y_encoded
    )

    # Transform features
    X_train_transformed = preprocessor.fit_transform(X_train)
    X_test_transformed = preprocessor.transform(X_test)

    return X_train_transformed, X_test_transformed, y_train, y_test, preprocessor, label_classes
