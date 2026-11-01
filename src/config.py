"""Loads and validates project configuration from config.yaml."""

from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: Path | None = None) -> dict:
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    _resolve_paths(cfg)
    return cfg


def _resolve_paths(cfg: dict) -> None:
    """Convert relative paths in config to absolute paths anchored at PROJECT_ROOT."""
    paths = cfg.get("paths", {})
    for key in ("raw_data_dir", "processed_data_dir", "database", "visualizations_dir"):
        if key in paths:
            paths[key] = str(PROJECT_ROOT / paths[key])


def get_column_map(cfg: dict) -> dict:
    return cfg.get("column_mapping", {})


def get_grade_map(cfg: dict) -> dict:
    return cfg.get("grade_mapping", {})


def get_cost_params(cfg: dict) -> dict:
    return cfg.get("cost_model", {})


def get_analysis_params(cfg: dict) -> dict:
    return cfg.get("analysis", {})
