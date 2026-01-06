from __future__ import annotations

import errno
import functools
import hashlib
import os
import re
import shutil
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml


NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")

# Boolean true/false string values
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


@functools.lru_cache(maxsize=2048)
def normalize_token(value: str) -> str:
    """Return a normalized token suitable for fuzzy comparisons."""
    lowered = value.lower()
    stripped = NORMALIZE_PATTERN.sub("", lowered)
    return stripped


def clear_normalize_cache() -> None:
    """Clear the normalize_token LRU cache.

    Useful for testing to ensure deterministic behavior and for memory
    management in long-running processes.
    """
    normalize_token.cache_clear()


def get_normalize_cache_info() -> functools._CacheInfo:
    """Return cache statistics for the normalize_token LRU cache.

    Returns a named tuple with fields: hits, misses, maxsize, currsize.
    Useful for debugging and performance monitoring.
    """
    return normalize_token.cache_info()


def slugify(value: str, separator: str = "-") -> str:
    """Create a slug suitable for file system usage."""
    normalized = normalize_token(value)
    words = [word for word in re.split(r"[^a-z0-9]+", value.lower()) if word]
    if not words:
        return normalized or "item"
    return separator.join(words)


SAFE_FILENAME_CHARS = set(string.ascii_letters + string.digits + "-_. ()[]")


def sanitize_component(component: str, replacement: str = "_") -> str:
    component = component.strip()
    if not component:
        return "untitled"

    cleaned = "".join(ch if ch in SAFE_FILENAME_CHARS else replacement for ch in component)
    cleaned = re.sub(r"%s+" % re.escape(replacement), replacement, cleaned)
    cleaned = cleaned.strip(replacement) or "untitled"

    if cleaned in {".", ".."}:
        return "untitled"

    return cleaned


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: expand_env(val) for key, val in value.items()}
    return value


def load_yaml_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return expand_env(data)


def dump_yaml_file(path: Path, data: Dict[str, Any]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def hash_text(text: str) -> str:
    """Compute SHA-256 digest of the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha1_of_file(path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA-1 digest of the given file."""
    digest = hashlib.sha1()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:  # pragma: no cover - filesystem specific
        raise ValueError(f"Unable to hash {path}: {exc}") from exc
    return digest.hexdigest()


@dataclass
class LinkResult:
    created: bool
    reason: Optional[str] = None


def link_file(source: Path, destination: Path, mode: str = "hardlink") -> LinkResult:
    ensure_directory(destination.parent)

    if destination.exists():
        return LinkResult(created=False, reason="destination-exists")

    try:
        if mode == "hardlink":
            os.link(source, destination)
        elif mode == "copy":
            shutil.copy2(source, destination)
        elif mode == "symlink":
            destination.symlink_to(source)
        else:
            raise ValueError(f"Unsupported link mode: {mode}")
    except OSError as exc:
        if mode == "hardlink" and exc.errno in {errno.EXDEV, errno.EPERM}:
            try:
                shutil.copy2(source, destination)
                return LinkResult(created=True)
            except Exception as copy_exc:  # noqa: BLE001
                return LinkResult(created=False, reason=str(copy_exc))
        return LinkResult(created=False, reason=str(exc))
    except Exception as exc:  # noqa: BLE001
        return LinkResult(created=False, reason=str(exc))

    return LinkResult(created=True)


def parse_env_bool(value: Optional[str]) -> Optional[bool]:
    """Parse a boolean from an environment variable string.

    Returns None if value is None or not a recognized boolean string.
    """
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    return None


def env_bool(name: str) -> Optional[bool]:
    """Get a boolean from an environment variable.

    Returns None if not set or not a recognized boolean string.
    """
    return parse_env_bool(os.getenv(name))


def env_list(name: str, separator: str = ",") -> Optional[List[str]]:
    """Get a list of strings from an environment variable.

    Returns None if not set, empty list if set but empty.
    """
    raw = os.getenv(name)
    if raw is None:
        return None
    parts = [part.strip() for part in raw.split(separator) if part.strip()]
    return parts


def validate_url(url: Optional[str]) -> bool:
    """Validate that URL is a valid http/https URL."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:  # noqa: BLE001 - defensive
        return False
