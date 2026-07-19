"""Portable path helpers for QA / exhibit tooling.

Manifest ``uri`` values are repo-relative POSIX paths (forward slashes). Docker
Desktop on Windows may still need Windows-form host paths when the CLI is
``docker.exe`` invoked from WSL — see ``to_docker_path``.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path, PurePosixPath

LOG = logging.getLogger("xibo_qa.paths")

_WSL_MOUNT_RE = re.compile(r"^/mnt/([a-zA-Z])/(.*)$")
_WIN_ABS_RE = re.compile(r"^([A-Za-z]):/(.*)$")


def resolve_manifest_path(uri: str, *, root: Path) -> Path:
    """Resolve a manifest/timeline ``uri`` to a host filesystem path.

    - Repo-relative URIs always use POSIX separators (``exhibits/slug/...``).
    - Absolute POSIX paths (``/…``) are kept as-is.
    - Absolute Windows paths (``C:/…``) work on native Windows; under WSL they
      map to ``/mnt/<drive>/…`` so scripts never depend on Win32 path syntax.
    """
    text = (uri or "").strip().replace("\\", "/")
    if not text:
        raise ValueError("empty uri")

    win = _WIN_ABS_RE.match(text)
    if win:
        drive, rest = win.group(1), win.group(2)
        if os.name == "nt":
            return Path(f"{drive}:/{rest}" if rest else f"{drive}:/")
        # Running under Linux/WSL: never keep ``C:/…`` as a relative fragment.
        return Path(f"/mnt/{drive.lower()}/{rest}" if rest else f"/mnt/{drive.lower()}")

    posix = PurePosixPath(text)
    if posix.is_absolute():
        return Path(text)

    return root.joinpath(*posix.parts)


@lru_cache(maxsize=1)
def docker_client_os() -> str:
    """Return docker client OS (`windows`, `linux`, …). Empty string if unknown."""
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Client.Os}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        os_name = (result.stdout or "").strip().lower()
        if os_name in {"windows", "linux", "darwin"}:
            return os_name
    except (OSError, subprocess.SubprocessError):
        pass

    # WSL often wraps Windows docker.exe; the stub CLI prints an error and no Os.
    if _running_in_wsl() and _docker_invokes_windows_cli():
        return "windows"
    return ""


def _running_in_wsl() -> bool:
    try:
        proc_version = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return "microsoft" in proc_version or "wsl" in proc_version


def _docker_invokes_windows_cli() -> bool:
    docker_path = shutil.which("docker")
    if not docker_path:
        return bool(shutil.which("docker.exe"))
    if docker_path.lower().endswith(".exe"):
        return True
    try:
        # Small shell wrappers (e.g. ~/bin/docker) typically exec docker.exe.
        if Path(docker_path).stat().st_size < 8192:
            body = Path(docker_path).read_text(encoding="utf-8", errors="ignore")
            if "docker.exe" in body:
                return True
    except OSError:
        pass
    return bool(shutil.which("docker.exe"))


def to_docker_path(path: Path | str) -> str:
    """Translate host paths for the active Docker CLI.

    When WSL calls Windows ``docker.exe``, Linux paths like ``/mnt/c/Users/...``
    are misread as ``C:\\mnt\\c\\Users\\...``. Convert them to ``C:\\Users\\...``.
    Native Linux Docker keeps POSIX paths unchanged.
    """
    resolved = Path(path).resolve()
    text = str(resolved)
    if docker_client_os() != "windows":
        return text

    match = _WSL_MOUNT_RE.match(text)
    if match:
        drive = match.group(1).upper()
        rest = match.group(2).replace("/", "\\")
        converted = f"{drive}:\\{rest}" if rest else f"{drive}:\\"
        LOG.debug("docker path %s -> %s", text, converted)
        return converted

    # Already a Windows path produced on a WinPython host.
    return text
