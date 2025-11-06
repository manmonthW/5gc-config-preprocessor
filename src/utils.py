"""
Utility helpers for the configuration preprocessor project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union


def resolve_config_path(config_path: Union[str, Path]) -> Path:
    """
    Resolve the configuration file path with sensible fallbacks.

    Each module may be instantiated from different working directories (e.g.
    test runners), so relative paths like "../config.yaml" should still locate
    the project-level copy. This helper attempts a series of locations before
    failing with FileNotFoundError.
    """
    path = Path(config_path).expanduser()

    # 1. Absolute or already correct relative path.
    if path.is_absolute() and path.exists():
        return path
    if not path.is_absolute() and path.exists():
        return path.resolve()

    # 2. Relative to current working directory.
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    # 3. Relative to the src directory or project root.
    src_dir = Path(__file__).resolve().parent
    project_root = src_dir.parent
    for base in (src_dir, project_root):
        candidate = (base / path).resolve()
        if candidate.exists():
            return candidate

    # 4. Fallback: search by filename under project root.
    if path.name:
        for candidate in project_root.glob(path.name):
            if candidate.is_file():
                return candidate.resolve()

    raise FileNotFoundError(f"Configuration file not found: {config_path}")

