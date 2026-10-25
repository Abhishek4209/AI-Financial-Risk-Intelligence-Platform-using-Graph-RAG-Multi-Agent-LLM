"""Shared helpers for configuration, paths, and JSON-safe values."""

import json
import os
from pathlib import Path
from typing import Any



def resolve_path(value: str | Path, *, root: Path | None = None) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
                path = (root or Path(__file__).resolve().parents[2]) / path
        return path.resolve()



def load_yaml(path: str | Path) -> dict[str, Any]:
        try:
                import yaml
        except ImportError as exc:
                raise RuntimeError("Install PyYAML to load YAML configuration") from exc
        with Path(path).open(encoding="utf-8") as source:
                value = yaml.safe_load(source) or {}
        if not isinstance(value, dict):
                raise ValueError("Configuration root must be a mapping: %s" % path)
        return value



def env_or_config(name: str, config: dict[str, Any], key: str, default: Any = None) -> Any:
        return os.getenv(name, config.get(key, default))



def json_safe(value: Any) -> Any:
        try:
                import numpy as np
                if isinstance(value, np.generic):
                        return value.item()
                if isinstance(value, np.ndarray):
                        return value.tolist()
        except ImportError:
                pass
        if isinstance(value, dict):
                return {str(key): json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
                return [json_safe(item) for item in value]
        if hasattr(value, "isoformat"):
                return value.isoformat()
        return value



def json_dumps(value: Any) -> str:
        return json.dumps(json_safe(value), ensure_ascii=False, default=str)
