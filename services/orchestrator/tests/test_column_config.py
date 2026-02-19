"""Tests for ColumnConfig schema, suggest_column_config heuristics, and pipeline integration."""

import uuid
import pandas as pd
import numpy as np
import pytest

from app.schemas.plan import ColumnConfig, ExperimentRunRequest, SuggestColumnsResponse
from app.services.profiler import profile_dataset, suggest_column_config
from app.preprocessing.pipeline import preprocess_dataset


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def iris_kaggle_df() -> pd.DataFrame:
    """Simulated Kaggle Iris CSV — includes an Id surrogate key."""
    return pd.DataFrame({
        "Id": range(1, 151),
        "SepalLengthCm": np.random.default_rng(0).uniform(4.0, 8.0, 150),
        "SepalWidthCm": np.random.default_rng(1).uniform(2.0, 4.5, 150),
        "PetalLengthCm": np.random.default_rng(2).uniform(1.0, 7.0, 150),
        "PetalWidthCm": np.random.default_rng(3).uniform(0.1, 2.5, 150),
        "Species": ["Iris-setosa"] * 50 + ["Iris-versicolor"] * 50 + ["Iris-virginica"] * 50,
    })


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestColumnConfigSchema:

    def test_defaults_are_empty(self):
        cfg = ColumnConfig()
        assert cfg.ignore_columns == []
        assert cfg.feature_columns == []
        assert cfg.source == "auto"

    def test_overlap_raises(self):
        with pytest.raises(ValueError, match="cannot appear in both"):
            ColumnConfig(ignore_columns=["Id"], feature_columns=["Id"])

    def test_no_overlap_does_not_raise(self):
        cfg = ColumnConfig(ignore_columns=["Id"], feature_columns=["SepalLength"])
        assert cfg.ignore_columns == ["Id"]
        assert cfg.feature_columns == ["SepalLength"]

    def test_source_auto(self):
        assert ColumnConfig(source="auto").source == "auto"

    def test_source_user(self):
        assert ColumnConfig(source="user").source == "user"

    def test_source_invalid_raises(self):
        with pytest.raises(Exception):
            ColumnConfig(source="system")

    def test_experiment_request_backwards_compat(self):
        """Existing callers without column_config must still work."""
        req = ExperimentRunRequest(
            dataset_id="abc",
            target_column="Species",
            model_names=["logistic_regression"],
            test_size=0.2
        )
        assert req.column_config is None

    def test_experiment_request_with_column_config(self):
        cfg = ColumnConfig(ignore_columns=["Id"], source="user")
        req = ExperimentRunRequest(
            dataset_id="abc",
            target_column="Species",
            model_names=["logistic_regression"],
            test_size=0.2,
            column_config=cfg
        )
        assert req.column_config.ignore_columns == ["Id"]
        assert req.column_config.source == "user"


# ---------------------------------------------------------------------------
# Heuristic tests
# ---------------------------------------------------------------------------

class TestSuggestColumnConfig:

    def test_detects_integer_id_column(self):
        df = iris_kaggle_df()
        profile = profile_dataset(df)
        config, notes = suggest_column_config(profile, target_column="Species")
        assert "Id" in config.ignore_columns
        assert "Id" in notes
        assert "ID column" in notes["Id"]

    def test_float_features_not_ignored(self):
        df = iris_kaggle_df()
        profile = profile_dataset(df)
        config, _ = suggest_column_config(profile, target_column="Species")
        for col in ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]:
            assert col not in config.ignore_columns

    def test_target_never_in_ignore_or_feature(self):
        df = iris_kaggle_df()
        profile = profile_dataset(df)
        config, notes = suggest_column_config(profile, target_column="Species")
        assert "Species" not in config.ignore_columns
        assert "Species" not in config.feature_columns
        assert "Species" not in notes

    def test_detects_constant_column(self):
        df = pd.DataFrame({
            "feature": [1.0, 2.0, 3.0, 4.0, 5.0],
            "constant": ["x", "x", "x", "x", "x"],
            "target": [0, 1, 0, 1, 0]
        })
        profile = profile_dataset(df)
        config, notes = suggest_column_config(profile, target_column="target")
        assert "constant" in config.ignore_columns
        assert "constant column" in notes["constant"]

    def test_detects_high_cardinality_string(self):
        df = pd.DataFrame({
            "uuid_col": [str(uuid.uuid4()) for _ in range(100)],
            "feature": range(100),
            "target": [0, 1] * 50
        })
        profile = profile_dataset(df)
        config, notes = suggest_column_config(profile, target_column="target")
        assert "uuid_col" in config.ignore_columns
        assert "high-cardinality" in notes["uuid_col"]

    def test_feature_columns_empty_by_default(self):
        df = iris_kaggle_df()
        profile = profile_dataset(df)
        config, _ = suggest_column_config(profile, target_column="Species")
        assert config.feature_columns == []

    def test_source_is_auto(self):
        df = iris_kaggle_df()
        profile = profile_dataset(df)
        config, _ = suggest_column_config(profile, target_column="Species")
        assert config.source == "auto"

    def test_float_with_100_pct_unique_not_ignored(self):
        """Continuous float features with high uniqueness must NOT be treated as IDs."""
        df = pd.DataFrame({
            "salary": np.random.default_rng(42).uniform(30000, 120000, 50),
            "target": [0, 1] * 25
        })
        profile = profile_dataset(df)
        config, _ = suggest_column_config(profile, target_column="target")
        assert "salary" not in config.ignore_columns


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

class TestPreprocessWithColumnConfig:

    def test_no_config_uses_all_columns_including_id(self):
        df = iris_kaggle_df()
        X_train, X_test, *_ = preprocess_dataset(df, "Species", 0.2, column_config=None)
        # Id + 4 measurements = 5 numeric features
        assert X_train.shape[1] == 5

    def test_ignore_id_reduces_feature_count(self):
        df = iris_kaggle_df()
        cfg = ColumnConfig(ignore_columns=["Id"])
        X_train, X_test, *_ = preprocess_dataset(df, "Species", 0.2, column_config=cfg)
        assert X_train.shape[1] == 4

    def test_feature_allowlist_restricts_to_subset(self):
        df = iris_kaggle_df()
        cfg = ColumnConfig(
            ignore_columns=["Id"],
            feature_columns=["SepalLengthCm", "PetalLengthCm"]
        )
        X_train, X_test, *_ = preprocess_dataset(df, "Species", 0.2, column_config=cfg)
        assert X_train.shape[1] == 2

    def test_nonexistent_ignore_column_silently_skipped(self):
        df = iris_kaggle_df()
        cfg = ColumnConfig(ignore_columns=["NonExistent", "Id"])
        X_train, *_ = preprocess_dataset(df, "Species", 0.2, column_config=cfg)
        assert X_train.shape[1] == 4  # Only Id actually dropped

    def test_no_nan_after_column_config_applied(self):
        df = iris_kaggle_df()
        cfg = ColumnConfig(ignore_columns=["Id"])
        X_train, X_test, y_train, y_test, _, label_classes = preprocess_dataset(
            df, "Species", 0.2, column_config=cfg
        )
        assert not np.isnan(X_train).any()
        assert not np.isnan(X_test).any()

    def test_train_test_split_sizes_unchanged(self):
        df = iris_kaggle_df()
        cfg = ColumnConfig(ignore_columns=["Id"])
        X_train, X_test, y_train, y_test, _, _ = preprocess_dataset(
            df, "Species", 0.2, column_config=cfg
        )
        assert X_train.shape[0] == 120
        assert X_test.shape[0] == 30

    def test_label_classes_correct(self):
        df = iris_kaggle_df()
        cfg = ColumnConfig(ignore_columns=["Id"])
        *_, label_classes = preprocess_dataset(df, "Species", 0.2, column_config=cfg)
        assert len(label_classes) == 3
        assert "Iris-setosa" in label_classes

    def test_full_suggest_then_preprocess_pipeline(self):
        """Integration: suggest_column_config result feeds directly into preprocess_dataset."""
        df = iris_kaggle_df()
        profile = profile_dataset(df)
        cfg, notes = suggest_column_config(profile, "Species")

        assert "Id" in cfg.ignore_columns

        X_train, X_test, y_train, y_test, _, label_classes = preprocess_dataset(
            df, "Species", 0.2, column_config=cfg
        )
        assert X_train.shape[0] == 120
        assert X_test.shape[0] == 30
        assert X_train.shape[1] == 4  # Id dropped, 4 measurements remain
        assert not np.isnan(X_train).any()
        assert len(label_classes) == 3
