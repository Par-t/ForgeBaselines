"""Text preprocessing utilities — shared between classification and IR pipelines."""

import re
import string

import nltk
import pandas as pd

# Download required NLTK data at import time (no-op if already present)
nltk.download("punkt_tab", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("stopwords", quiet=True)

from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.corpus import stopwords

_stemmer = PorterStemmer()
_lemmatizer = WordNetLemmatizer()
_stop_words = set(stopwords.words("english"))


def preprocess_text(text: str, config) -> str:
    """Apply text preprocessing steps to a single string.

    Steps applied in order (when enabled):
        1. Lowercase
        2. Punctuation removal
        3. Stop-word removal
        4. Stemming (Porter) — mutually exclusive with lemmatization
        5. Lemmatization (WordNet) — mutually exclusive with stemming
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    if config.lowercase:
        text = text.lower()

    if config.remove_punctuation:
        text = text.translate(str.maketrans("", "", string.punctuation))

    # Tokenize for word-level operations
    if config.remove_stopwords or config.stemming or config.lemmatization:
        tokens = text.split()

        if config.remove_stopwords:
            tokens = [t for t in tokens if t not in _stop_words]

        if config.stemming:
            tokens = [_stemmer.stem(t) for t in tokens]
        elif config.lemmatization:
            tokens = [_lemmatizer.lemmatize(t) for t in tokens]

        text = " ".join(tokens)

    return text


def preprocess_text_column(series: pd.Series, config) -> pd.Series:
    """Apply text preprocessing to every cell in a Series."""
    return series.apply(lambda x: preprocess_text(x, config))


def is_text_column(series: pd.Series) -> bool:
    """Heuristic: object dtype with high cardinality is a text column.

    A column is considered text (rather than low-cardinality categorical) if:
    - dtype is object
    - unique ratio > 0.3  OR  median string length > 20
    """
    if series.dtype != object:
        return False
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    unique_ratio = non_null.nunique() / len(non_null)
    median_len = non_null.astype(str).str.len().median()
    return unique_ratio > 0.3 or median_len > 20
