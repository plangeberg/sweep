"""Config loader with template/override pattern and validation."""

import json
import os
import sys
from pathlib import Path


DEFAULT_CONFIG = {
    "paths": [],
    "output": {
        "database": "sweep.db",
        "log_file": "sweep.log",
        "status_file": "sweep-status.json",
    },
    "crawler": {
        "throttle_ms": 500,
        "hash_files": False,
        "max_depth": 20,
        "skip_dirs": [
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "$RECYCLE.BIN", "System Volume Information", ".vs", "bin", "obj",
        ],
        "skip_extensions": [],
        "batch_commit_size": 500,
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, recursing into nested dicts."""
    result = base.copy()
    for key, value in override.items():
        if key.startswith("_"):
            continue  # skip comments
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str) -> dict:
    """Load and validate config from JSON file."""
    path = Path(config_path)
    if not path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        print("  Copy config.template.json to config.json and set your paths.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {config_path}: {e}", file=sys.stderr)
        sys.exit(1)

    config = deep_merge(DEFAULT_CONFIG, user_config)
    validate_config(config, config_path)
    return config


def validate_config(config: dict, config_path: str) -> None:
    """Validate config values. Exit with helpful message on error."""
    errors = []

    # Paths
    if not config["paths"]:
        errors.append("No paths configured. Set paths[] in your config file.")

    for p in config["paths"]:
        if "REPLACE_ME" in p:
            errors.append(f"Path contains placeholder: '{p}' — replace with a real path.")
        elif not os.path.exists(p):
            # Warning, not error — path might be a network share that's currently offline
            print(f"WARNING: Path does not exist (will skip if unreachable): {p}", file=sys.stderr)

    # Output
    db_path = config["output"]["database"]
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if not os.path.isdir(db_dir):
        errors.append(f"Database directory does not exist: {db_dir}")

    # Crawler
    throttle = config["crawler"]["throttle_ms"]
    if not isinstance(throttle, (int, float)) or throttle < 0:
        errors.append(f"throttle_ms must be >= 0, got: {throttle}")

    max_depth = config["crawler"]["max_depth"]
    if not isinstance(max_depth, int) or max_depth < 1:
        errors.append(f"max_depth must be >= 1, got: {max_depth}")

    batch_size = config["crawler"]["batch_commit_size"]
    if not isinstance(batch_size, int) or batch_size < 1:
        errors.append(f"batch_commit_size must be >= 1, got: {batch_size}")

    if errors:
        print(f"ERROR: Config validation failed ({config_path}):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
