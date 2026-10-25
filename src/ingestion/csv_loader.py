"""Validated CSV loading with optional chunk iteration."""

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.preprocessing.cleaner import clean_frame
from src.utils.validators import require_columns



def load_csv(path: str | Path, *, required_columns: Sequence[str] = (), **read_options: Any) -> pd.DataFrame:
        source = Path(path).expanduser()
        if not source.is_file():
                raise FileNotFoundError("CSV not found: %s" % source)
        options = {"encoding": "utf-8-sig", "low_memory": False}
        options.update(read_options)
        frame = clean_frame(pd.read_csv(source, **options))
        require_columns(frame.columns, required_columns, source=str(source))
        return frame



def iter_csv(path: str | Path, *, chunksize: int = 100_000, required_columns: Sequence[str] = (), **read_options: Any) -
> Iterator[pd.DataFrame]:
        source = Path(path).expanduser()
        if not source.is_file():
                raise FileNotFoundError("CSV not found: %s" % source)
        if chunksize < 1:
                raise ValueError("chunksize must be positive")
        reader = pd.read_csv(source, chunksize=chunksize, encoding="utf-8-sig", **read_options)
        for chunk in reader:
                cleaned = clean_frame(chunk)
                require_columns(cleaned.columns, required_columns, source=str(source))
                yield cleaned



def load_csv_documents(path: str | Path, *, text_columns: Sequence[str] | None = None) -> list[dict[str, Any]]:
        frame = load_csv(path)
        columns = list(text_columns or frame.columns)
        require_columns(frame.columns, columns, source=str(path))
        return [
                {"page_content": " | ".join("%s: %s" % (column, row[column]) for column in columns if
pd.notna(row[column])),
                 "metadata": {"source_file": Path(path).name, "row": int(index) + 2}}
                for index, row in frame.iterrows()
        ]
