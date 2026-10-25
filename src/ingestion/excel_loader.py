"""Excel workbook loading with sheet selection and schema validation."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.preprocessing.cleaner import clean_frame
from src.utils.validators import require_columns



def load_excel(path: str | Path, *, sheet_name: str | int = 0, required_columns: Sequence[str] = (), **options: Any) ->
pd.DataFrame:
        source = Path(path).expanduser()
        if not source.is_file():
                raise FileNotFoundError("Excel workbook not found: %s" % source)
        frame = clean_frame(pd.read_excel(source, sheet_name=sheet_name, **options))
        require_columns(frame.columns, required_columns, source=str(source))
        return frame
