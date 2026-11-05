"""Portable path helpers for tools/ (manifest URI resolution)."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath

_WIN_ABS_RE = re.compile(r"^([A-Za-z]):/(.*)$")


def resolve_manifest_path(uri: str, *, root: Path) -> Path:
    """Resolve a manifest/timeline ``uri`` to a host filesystem path.

    - Repo-relative URIs use POSIX separators (``exhibits/slug/...``).
    - Absolute POSIX paths are kept as-is.
    - Absolute Windows paths (``C:/…``) work on native Windows; under WSL they
      map to ``/mnt/<drive>/…``.
    """
    text = (uri or "").strip().replace("\\", "/")
    if not text:
        raise ValueError("empty uri")

    win = _WIN_ABS_RE.match(text)
    if win:
        drive, rest = win.group(1), win.group(2)
        if os.name == "nt":
            return Path(f"{drive}:/{rest}" if rest else f"{drive}:/")
        return Path(f"/mnt/{drive.lower()}/{rest}" if rest else f"/mnt/{drive.lower()}")

    posix = PurePosixPath(text)
    if posix.is_absolute():
        return Path(text)

    return root.joinpath(*posix.parts)
