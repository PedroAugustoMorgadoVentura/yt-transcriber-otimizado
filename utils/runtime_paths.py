import os
import sys
from pathlib import Path


def get_runtime_root() -> Path:
    """Return the application root that works for both source runs and Nuitka bundles."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resolve_runtime_path(*parts: str) -> Path:
    """Resolve a path relative to the application root, supporting standalone builds."""
    return get_runtime_root().joinpath(*parts)


def ensure_runtime_dir(*parts: str) -> Path:
    path = resolve_runtime_path(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_runtime_env_path() -> str:
    return str(get_runtime_root())
