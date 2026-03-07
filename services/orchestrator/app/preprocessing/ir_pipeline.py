"""IR-specific preprocessing: apply text preprocessing to corpus and queries."""

from typing import Optional, Tuple

import pandas as pd

from app.schemas.classification import PreprocessingConfig
from app.preprocessing.text import preprocess_text_column


def preprocess_ir_datasets(
    corpus_df: pd.DataFrame,
    queries_df: pd.DataFrame,
    text_column: str,
    preprocessing_config: Optional[PreprocessingConfig] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Apply text preprocessing to corpus text column and query column.

    Always preprocesses the named text_column in corpus and the 'query' column
    in queries (unlike pipeline.py which uses the is_text_column heuristic).

    Returns (preprocessed_corpus_df, preprocessed_queries_df).
    """
    corpus_out = corpus_df.copy()
    queries_out = queries_df.copy()

    if preprocessing_config is not None and preprocessing_config.text is not None:
        cfg = preprocessing_config.text
        corpus_out[text_column] = preprocess_text_column(corpus_out[text_column], cfg)
        queries_out["query"] = preprocess_text_column(queries_out["query"], cfg)

    return corpus_out, queries_out
