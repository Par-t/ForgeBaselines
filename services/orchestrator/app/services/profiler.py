"""Dataset profiling service."""

import pandas as pd
from typing import Dict, Any, Tuple

from app.schemas.plan import ColumnConfig


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


def suggest_column_config(
    profile: Dict[str, Any],
    target_column: str
) -> Tuple[ColumnConfig, Dict[str, str]]:
    """Apply heuristics to profiler output to produce a suggested ColumnConfig.

    Heuristics (target column always skipped):
    1. Integer ID: int dtype AND cardinality == n_rows → ignore
    2. High-cardinality string: object dtype AND cardinality/n_rows > 0.9 → ignore
    3. Constant: cardinality == 1 → ignore

    Returns (ColumnConfig with source="auto", column_notes mapping col → reason string).
    """
    n_rows = profile["n_rows"]
    column_types = profile["column_types"]
    cardinality = profile["cardinality"]

    ignore_columns = []
    column_notes = {}

    for col in profile["column_names"]:
        if col == target_column:
            continue

        dtype = column_types[col]
        card = cardinality[col]

        # Heuristic 1: integer surrogate key (100% unique integers)
        if dtype in ("int64", "int32") and card == n_rows:
            ignore_columns.append(col)
            column_notes[col] = (
                f"auto-detected as ID column "
                f"(integer dtype '{dtype}', {card}/{n_rows} unique values = 100%)"
            )
            continue

        # Heuristic 2: high-cardinality string (UUID / free text)
        if dtype == "object" and n_rows > 0 and card / n_rows > 0.9:
            ignore_columns.append(col)
            column_notes[col] = (
                f"auto-detected as high-cardinality text/ID column "
                f"(object dtype, {card}/{n_rows} unique = {card/n_rows:.0%})"
            )
            continue

        # Heuristic 3: constant column (zero information)
        if card == 1:
            ignore_columns.append(col)
            column_notes[col] = (
                f"auto-detected as constant column "
                f"(only 1 unique value across {n_rows} rows)"
            )

    config = ColumnConfig(
        ignore_columns=ignore_columns,
        feature_columns=[],
        source="auto"
    )
    return config, column_notes
