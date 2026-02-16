"""Dataset profiling service."""

import pandas as pd
from typing import Dict, Any


def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Profile a dataset and return statistics."""
    n_rows, n_cols = df.shape

    # Column types
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

    # Missing values
    missing_by_column = df.isnull().sum().to_dict()
    total_missing = sum(missing_by_column.values())

    # Cardinality
    cardinality = {col: int(df[col].nunique()) for col in df.columns}

    # Memory
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "numeric_cols": len(numeric_cols),
        "categorical_cols": len(categorical_cols),
        "column_names": df.columns.tolist(),
        "column_types": {col: str(df[col].dtype) for col in df.columns},
        "missing_values": int(total_missing),
        "missing_by_column": {k: int(v) for k, v in missing_by_column.items()},
        "cardinality": cardinality,
        "memory_mb": round(memory_mb, 2)
    }
