#!/usr/bin/env python3
"""Ephemeral Xibo CMS visual QA pipeline.

Spins up docker-compose.test.yml, drives the Xibo REST API (OAuth2 client
credentials), builds a multi-region layout from exhibits/<slug>/layouts/timeline.yaml
when present, publishes it to CMS, forces an XMR collectNow sync when available,
and captures the headless Xibo Linux Player framebuffer (screenshot + N-second MP4,
default 30s). Use --preview-only for the Chromium timeline-preview escape hatch.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from pathutil import resolve_manifest_path, to_docker_path
from PIL import Image, ImageDraw, ImageStat

LOG = logging.getLogger("xibo_qa")

QA_DIR = Path(__file__).resolve().parent
REPO_ROOT = QA_DIR.parent.parent
EXHIBITS_DIR = REPO_ROOT / "exhibits"
COMPOSE_FILE = QA_DIR / "docker-compose.test.yml"
PLAYER_RUNTIME_DIR = QA_DIR / "player-runtime"
DEFAULT_ARTIFACT_DIR = QA_DIR / "artifacts"
DEFAULT_FIXTURE = QA_DIR / "fixtures" / "qa-sample.png"
DEFAULT_EXHIBIT_SLUG = "humpback-migration"
DEFAULT_RECORD_DURATION = 30
PLAYER_CONTAINER = "xibo-qa-kiosk-player"
CMS_CONTAINER = "xibo-qa-cms-web"
EXPECTED_SIZE = (1920, 1080)
_IMAGE_MIME_PREFIX = "image/"


class PipelineError(RuntimeError):
    """Fatal pipeline failure."""


@dataclass
class Settings:
    cms_url: str
    admin_user: str
    admin_password: str
    client_id: str
    client_secret: str
    cms_key: str
    display_name: str
    layout_name: str
    capture_wait_seconds: int
    compose_project: str
    artifact_dir: Path
    media_path: Path
    exhibit_slug: str
    record_duration: int
    keep_stack: bool
    skip_up: bool
    preview_only: bool
    fast: bool
    rebuild_player: bool
    record_video: bool
    skip_html_packages: bool
    image_only_layout: bool

    @classmethod
    def from_env(cls, args: argparse.Namespace) -> "Settings":
        load_dotenv_files()
        artifact_dir = Path(args.artifact_dir or os.environ.get("QA_ARTIFACT_DIR", DEFAULT_ARTIFACT_DIR))
        exhibit_slug = (
            args.exhibit
            or os.environ.get("QA_EXHIBIT_SLUG", "").strip()
            or DEFAULT_EXHIBIT_SLUG
        )
        fast = bool(getattr(args, "fast", False)) or (
            os.environ.get("QA_FAST", "").strip().lower() in {"1", "true", "yes"}
        )
        # Normal runs rebuild the player image; --fast reuses it unless --rebuild-player.
        rebuild_player = bool(getattr(args, "rebuild_player", False))
        if not fast and not rebuild_player:
            rebuild_player = True
        if fast and not getattr(args, "rebuild_player", False):
            rebuild_player = False
        if os.environ.get("QA_REBUILD_PLAYER", "").strip().lower() in {"1", "true", "yes"}:
            rebuild_player = True

        default_duration = 5 if fast else DEFAULT_RECORD_DURATION
        record_duration = int(
            args.duration
            if args.duration is not None
            else os.environ.get("QA_RECORD_DURATION", default_duration)
        )
        if record_duration < 1:
            raise PipelineError("--duration / QA_RECORD_DURATION must be >= 1")

        media_override = args.media or os.environ.get("QA_MEDIA_PATH", "").strip()
        if media_override:
            media_path = Path(media_override)
        else:
            media_path = resolve_exhibit_media(exhibit_slug)

        layout_default = f"qa-{exhibit_slug}"
        preview_only = bool(getattr(args, "preview_only", False)) or (
            os.environ.get("QA_USE_TIMELINE_PREVIEW", "").strip().lower() in {"1", "true", "yes"}
        )
        default_wait = 20 if fast else 45
        if args.capture_wait is not None:
            capture_wait = int(args.capture_wait)
        elif fast:
            # Ignore a high QA_CAPTURE_WAIT_SECONDS from config.env during --fast.
            capture_wait = default_wait
        else:
            capture_wait = int(os.environ.get("QA_CAPTURE_WAIT_SECONDS", default_wait))
        keep_stack = bool(args.keep_stack) or fast
        # PNG-only in --fast unless --record-video (or an explicit long --duration).
        record_video = not fast
        if getattr(args, "record_video", False):
            record_video = True
        if getattr(args, "no_video", False):
            record_video = False

        # Headless Xvfb: skip HTML packages by default (WebKitGTK paint crashes).
        # Override with QA_SKIP_HTML_PACKAGES=0 or --include-html-packages.
        skip_html_env = os.environ.get("QA_SKIP_HTML_PACKAGES", "").strip().lower()
        if getattr(args, "include_html_packages", False):
            skip_html_packages = False
        elif getattr(args, "skip_html_packages", False):
            skip_html_packages = True
        elif skip_html_env in {"0", "false", "no"}:
            skip_html_packages = False
        elif skip_html_env in {"1", "true", "yes"}:
            skip_html_packages = True
        else:
            # Default on for player mode; off for Chromium preview.
            skip_html_packages = not preview_only

        image_only_layout = bool(getattr(args, "image_only_layout", False)) or (
            os.environ.get("QA_IMAGE_ONLY_LAYOUT", "").strip().lower() in {"1", "true", "yes"}
        )

        return cls(
            cms_url=os.environ.get("XIBO_CMS_URL", "http://127.0.0.1:8080").rstrip("/"),
            admin_user=os.environ.get("XIBO_ADMIN_USER", "xibo_admin"),
            admin_password=os.environ.get("XIBO_ADMIN_PASSWORD", "password"),
            client_id=os.environ.get("XIBO_CLIENT_ID", "").strip(),
            client_secret=os.environ.get("XIBO_CLIENT_SECRET", "").strip(),
            cms_key=os.environ.get("XIBO_CMS_KEY", "").strip(),
            display_name=os.environ.get("XIBO_DISPLAY_NAME", "qa-kiosk-01"),
            layout_name=(os.environ.get("QA_LAYOUT_NAME", "").strip() or layout_default),
            capture_wait_seconds=capture_wait,
            compose_project=os.environ.get("QA_COMPOSE_PROJECT", "xibo-qa"),
            artifact_dir=artifact_dir,
            media_path=media_path,
            exhibit_slug=exhibit_slug,
            record_duration=record_duration,
            keep_stack=keep_stack,
            skip_up=bool(args.skip_up),
            preview_only=preview_only,
            fast=fast,
            rebuild_player=rebuild_player,
            record_video=record_video,
            skip_html_packages=skip_html_packages,
            image_only_layout=image_only_layout,
        )


def load_dotenv_files() -> None:
    """Load ops/qa/config.env and repo .env without overriding existing env vars."""
    for path in (QA_DIR / "config.env", REPO_ROOT / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def run_cmd(
    args: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    timeout: Optional[int] = None,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    LOG.debug("exec: %s", " ".join(args))
    result = subprocess.run(
        args,
        check=False,
        capture_output=capture,
        text=True,
        timeout=timeout,
        env=env,
    )
    if check and result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or f"exit {result.returncode}"
        raise PipelineError(f"Command failed ({result.returncode}): {' '.join(args)}\n{detail}")
    return result


def compose_cmd(settings: Settings, *extra: str) -> list[str]:
    env_file = QA_DIR / "config.env"
    # Written by provision_player_cms_config so compose interpolation sees the live
    # SERVER_KEY. Last --env-file wins over config.env's empty XIBO_CMS_KEY=.
    runtime_env = PLAYER_RUNTIME_DIR / "compose.runtime.env"
    cmd = [
        "docker",
        "compose",
        "-p",
        settings.compose_project,
        "-f",
        to_docker_path(COMPOSE_FILE),
    ]
    if env_file.is_file():
        cmd.extend(["--env-file", to_docker_path(env_file)])
    if runtime_env.is_file():
        cmd.extend(["--env-file", to_docker_path(runtime_env)])
    cmd.extend(extra)
    return cmd


# ---------------------------------------------------------------------------
# Visual verification
# ---------------------------------------------------------------------------


def verify_capture(
    image_path: Path,
    *,
    expected_size: tuple[int, int] = EXPECTED_SIZE,
    min_stddev: float = 8.0,
    max_black_ratio: float = 0.90,
    black_threshold: int = 12,
) -> dict[str, Any]:
    """Check screenshot structural integrity with Pillow.

    Validates:
    - exact pixel bounds (default 1920x1080)
    - not an unrendered near-black frame
    - sufficient luminance variance across the frame
    """
    if not image_path.is_file():
        raise PipelineError(f"Capture missing: {image_path}")

    with Image.open(image_path) as img:
        image = img.convert("RGB")
        width, height = image.size
        if (width, height) != expected_size:
            raise PipelineError(
                f"Unexpected capture size {width}x{height}; expected {expected_size[0]}x{expected_size[1]}"
            )

        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        mean = float(stat.mean[0])
        stddev = float(stat.stddev[0])

        # Sample every Nth pixel for black-ratio without loading a giant list of tuples.
        pixels = gray.getdata()
        step = max(1, len(pixels) // 200_000)
        sample = list(pixels)[::step]
        black_count = sum(1 for p in sample if p <= black_threshold)
        black_ratio = black_count / max(1, len(sample))

        result = {
            "path": str(image_path),
            "width": width,
            "height": height,
            "mean_luminance": round(mean, 3),
            "stddev_luminance": round(stddev, 3),
            "black_ratio": round(black_ratio, 4),
            "passed": True,
            "failures": [],
        }

        if black_ratio >= max_black_ratio:
            result["passed"] = False
            result["failures"].append(
                f"Frame appears unrendered/black (black_ratio={black_ratio:.3f} >= {max_black_ratio})"
            )
        if stddev < min_stddev:
            result["passed"] = False
            result["failures"].append(
                f"Insufficient pixel variance (stddev={stddev:.2f} < {min_stddev})"
            )

        if not result["passed"]:
            raise PipelineError(
                "Visual verification failed: " + "; ".join(result["failures"])
            )
        return result


def ensure_fixture_image(path: Path) -> Path:
    """Create a deterministic non-black 1920x1080 PNG if the fixture is missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return path

    LOG.info("Generating fixture image at %s", path)
    img = Image.new("RGB", EXPECTED_SIZE, (12, 74, 110))
    draw = ImageDraw.Draw(img)
    # Structured variance so Pillow checks pass on a known non-black frame.
    for y in range(0, EXPECTED_SIZE[1], 40):
        for x in range(0, EXPECTED_SIZE[0], 40):
            tone = 40 + ((x + y) % 180)
            draw.rectangle(
                [x, y, x + 19, y + 19],
                fill=(tone // 3, tone // 2, tone),
            )
    draw.rectangle([80, 80, 1840, 1000], outline=(230, 240, 255), width=8)
    draw.text((120, 120), "QA FIXTURE 1920x1080", fill=(240, 248, 255))
    img.save(path, format="PNG")
    return path


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise PipelineError(
            "PyYAML is required for exhibit resolution: pip install -r ops/qa/requirements.txt"
        ) from exc
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise PipelineError(f"YAML root must be a mapping: {path}")
    return data


def _local_paths_for_asset(exhibit_dir: Path, asset: dict[str, Any]) -> list[Path]:
    """Candidate host paths for a manifest asset (uri, assets/, previews/)."""
    candidates: list[Path] = []
    uri = str(asset.get("uri") or "").strip()
    if uri:
        candidates.append(resolve_manifest_path(uri, root=REPO_ROOT))
    filename = str(asset.get("filename") or "").strip()
    if filename:
        candidates.append(exhibit_dir / "media" / "assets" / filename)
    preview = str(asset.get("preview") or "").strip()
    if preview:
        candidates.append(exhibit_dir / "media" / "previews" / preview)
    return candidates


def resolve_exhibit_media(slug: str) -> Path:
    """Pick a local image for visual QA from exhibits/<slug>/media/manifest.yaml.

    Preference order:
    1. First ``scene-bg`` image with a readable local file
    2. First other image/* asset with a local file
    3. First ``*.jpg`` / ``*.png`` under ``media/previews/``
    """
    exhibit_dir = EXHIBITS_DIR / slug
    if not exhibit_dir.is_dir():
        raise PipelineError(f"Unknown exhibit slug (folder missing): {slug}")

    exhibit_yaml = exhibit_dir / "exhibit.yaml"
    if exhibit_yaml.is_file():
        exhibit = load_yaml(exhibit_yaml)
        yaml_slug = str(exhibit.get("slug") or "").strip()
        if yaml_slug and yaml_slug != slug:
            raise PipelineError(
                f"exhibit.yaml slug {yaml_slug!r} does not match folder {slug!r}"
            )

    manifest_path = exhibit_dir / "media" / "manifest.yaml"
    if not manifest_path.is_file():
        raise PipelineError(f"Missing media manifest: {manifest_path}")

    manifest = load_yaml(manifest_path)
    manifest_exhibit = str(manifest.get("exhibit") or "").strip()
    if manifest_exhibit and manifest_exhibit != slug:
        raise PipelineError(
            f"manifest.exhibit {manifest_exhibit!r} does not match folder {slug!r}"
        )

    assets = manifest.get("assets") or []
    if not isinstance(assets, list):
        raise PipelineError(f"manifest.assets must be a list: {manifest_path}")

    def first_existing(asset_list: list[dict[str, Any]]) -> Optional[Path]:
        for asset in asset_list:
            if not isinstance(asset, dict):
                continue
            for candidate in _local_paths_for_asset(exhibit_dir, asset):
                if candidate.is_file():
                    LOG.info(
                        "Resolved exhibit=%s media from asset id=%s -> %s",
                        slug,
                        asset.get("id"),
                        candidate,
                    )
                    return candidate
        return None

    scene_bgs = [
        a
        for a in assets
        if isinstance(a, dict)
        and a.get("role") == "scene-bg"
        and str(a.get("mime") or "").startswith(_IMAGE_MIME_PREFIX)
    ]
    chosen = first_existing(scene_bgs)
    if chosen is not None:
        return chosen

    images = [
        a
        for a in assets
        if isinstance(a, dict) and str(a.get("mime") or "").startswith(_IMAGE_MIME_PREFIX)
    ]
    chosen = first_existing(images)
    if chosen is not None:
        return chosen

    previews_dir = exhibit_dir / "media" / "previews"
    if previews_dir.is_dir():
        previews = sorted(
            [
                p
                for p in previews_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            ]
        )
        if previews:
            LOG.info("Resolved exhibit=%s media from preview -> %s", slug, previews[0])
            return previews[0]

    raise PipelineError(
        f"No local image found for exhibit {slug!r}. "
        "Add media under media/assets/ (or pass --media)."
    )


def ensure_media_ready(path: Path, *, allow_generate_fixture: bool) -> Path:
    """Ensure media exists; only auto-generate the default QA fixture."""
    if path.is_file():
        return path
    if allow_generate_fixture and path.resolve() == DEFAULT_FIXTURE.resolve():
        return ensure_fixture_image(path)
    raise PipelineError(f"Media file not found: {path}")


# ---------------------------------------------------------------------------
# Xibo API client
# ---------------------------------------------------------------------------


class XiboClient:
    def __init__(self, base_url: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "xibo-qa-pipeline/1.0"})
        self.timeout = timeout
        self.access_token: Optional[str] = None

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.request(method, self._url(path), **kwargs)
        if response.status_code >= 400:
            body = response.text[:2000]
            raise PipelineError(f"{method} {path} -> HTTP {response.status_code}: {body}")
        if not response.content:
            return None
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type or response.text[:1] in "{[":
            return response.json()
        return response.text

    def wait_until_ready(self, timeout_seconds: int = 300) -> None:
        deadline = time.time() + timeout_seconds
        last_error = "unknown"
        LOG.info("Waiting for CMS at %s", self.base_url)
        while time.time() < deadline:
            try:
                response = self.session.get(self._url("/login"), timeout=10)
                if response.status_code >= 500:
                    last_error = f"login HTTP {response.status_code}"
                    time.sleep(5)
                    continue

                probe = self.session.post(
                    self._url("/api/authorize/access_token"),
                    data={
                        "grant_type": "client_credentials",
                        "client_id": "probe",
                        "client_secret": "probe",
                    },
                    timeout=10,
                )
                # 400/401 means the OAuth endpoint is up; 5xx means still booting.
                if probe.status_code >= 500:
                    last_error = f"oauth HTTP {probe.status_code}"
                    time.sleep(5)
                    continue

                if not oauth_schema_ready():
                    last_error = "oauth_clients table not ready"
                    time.sleep(5)
                    continue

                if not mysql_scalar("SELECT `value` FROM `setting` WHERE `setting`='SERVER_KEY' LIMIT 1"):
                    last_error = "SERVER_KEY setting not ready"
                    time.sleep(5)
                    continue

                LOG.info(
                    "CMS is ready (login=%s oauth=%s schema=ok key=ok)",
                    response.status_code,
                    probe.status_code,
                )
                return
            except requests.RequestException as exc:
                last_error = str(exc)
            time.sleep(5)
        raise PipelineError(f"CMS not ready after {timeout_seconds}s: {last_error}")

    def obtain_token(self, client_id: str, client_secret: str) -> str:
        LOG.info("Requesting OAuth2 client_credentials token")
        payload = self.request(
            "POST",
            "/api/authorize/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = payload.get("access_token")
        if not token:
            raise PipelineError(f"Token response missing access_token: {payload}")
        self.access_token = token
        self.session.headers["Authorization"] = f"Bearer {token}"
        return token

    def bootstrap_application(
        self,
        admin_user: str,
        admin_password: str,
        app_name: str = "qa-pipeline",
    ) -> tuple[str, str]:
        """Provision a client_credentials Application for the ephemeral CMS.

        Prefer MySQL seeding (same approach as Xibo's own Cypress CI). Web UI
        login is brittle during first-boot and is only used as a secondary path.
        """
        del admin_user, admin_password  # reserved for optional web fallback
        client_id = secrets.token_hex(20)
        client_secret = secrets.token_hex(64)

        LOG.info("Bootstrapping OAuth application via MySQL seed")
        try:
            seed_oauth_client_mysql(client_id, client_secret, app_name)
            return client_id, client_secret
        except PipelineError as seed_exc:
            LOG.warning("MySQL OAuth seed failed (%s); trying web UI fallback", seed_exc)

        return self._bootstrap_application_via_web(client_id, client_secret, app_name)

    def _bootstrap_application_via_web(
        self,
        client_id: str,
        client_secret: str,
        app_name: str,
    ) -> tuple[str, str]:
        LOG.info("Bootstrapping OAuth application via admin web session")
        login_page = self.session.get(self._url("/login"), timeout=self.timeout)
        login_page.raise_for_status()

        csrf = _extract_html_value(login_page.text, "csrf_token")
        # Xibo login forms vary: username/password are the common Docker defaults.
        login_data: dict[str, str] = {
            "username": os.environ.get("XIBO_ADMIN_USER", "xibo_admin"),
            "password": os.environ.get("XIBO_ADMIN_PASSWORD", "password"),
        }
        if csrf:
            login_data["csrf_token"] = csrf
        login_resp = self.session.post(
            self._url("/login"),
            data=login_data,
            timeout=self.timeout,
            allow_redirects=True,
        )
        if login_resp.status_code >= 400:
            raise PipelineError(
                f"Admin login failed: HTTP {login_resp.status_code}: {login_resp.text[:500]}"
            )

        form = {
            "name": app_name,
            "authCode": 0,
            "clientCredentials": 1,
            "clientId": client_id,
            "clientSecret": client_secret,
        }
        if csrf:
            form["csrf_token"] = csrf

        for path in ("/application", "/application/add"):
            resp = self.session.post(
                self._url(path),
                data=form,
                timeout=self.timeout,
                allow_redirects=True,
            )
            if resp.status_code < 400:
                LOG.info("Created application via %s", path)
                return client_id, client_secret

        raise PipelineError("Unable to bootstrap OAuth application via web UI or MySQL")

    def get_setting(self, setting: str) -> Optional[str]:
        try:
            data = self.request("GET", "/api/settings", params={"setting": setting})
        except PipelineError as exc:
            LOG.debug("settings API unavailable for %s: %s", setting, exc)
            return None
        if isinstance(data, list) and data:
            return str(data[0].get("value") or data[0].get("settingValue") or "")
        if isinstance(data, dict):
            return str(data.get("value") or data.get(setting) or "")
        return None

    def get_cms_server_key(self) -> str:
        """Return the CMS secret key players use to register (SERVER_KEY)."""
        # Prefer DB — /api/settings is not reliably exposed on all CMS builds.
        key = mysql_scalar("SELECT `value` FROM `setting` WHERE `setting`='SERVER_KEY' LIMIT 1")
        if key:
            return key
        key = self.get_setting("SERVER_KEY") or ""
        if key:
            return key
        raise PipelineError(
            "Could not discover SERVER_KEY from MySQL setting table or API. "
            "Set XIBO_CMS_KEY in config.env."
        )

    def find_media_by_name(self, name: str) -> Optional[int]:
        """Return mediaId for an existing library item, or None."""
        try:
            payload = self.request("GET", "/api/library", params={"media": name, "exactName": 1})
        except PipelineError as exc:
            LOG.debug("library lookup failed for %s: %s", name, exc)
            return None
        items = payload if isinstance(payload, list) else payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            return None
        for item in items:
            if not isinstance(item, dict):
                continue
            item_name = str(item.get("name") or item.get("media") or "")
            if item_name.lower() == name.lower() or item_name.lower() == Path(name).stem.lower():
                media_id = _extract_id(item, keys=("mediaId", "id"))
                if media_id is not None:
                    return media_id
        # Fallback: first row when exactName filtered the list.
        if items and isinstance(items[0], dict):
            return _extract_id(items[0], keys=("mediaId", "id"))
        return None

    def upload_media(self, file_path: Path, name: Optional[str] = None) -> int:
        LOG.info("Uploading media %s", file_path)
        if not file_path.is_file():
            raise PipelineError(f"Media file not found: {file_path}")

        display_name = name or file_path.stem
        # Xibo HTML Package module accepts ``.htz`` (zip contents), not ``.zip``.
        # Use the stable display name as the upload basename so keep-stack reruns
        # collide predictably and we can reuse the existing library row.
        mime = _mime_for_path(file_path)
        if file_path.suffix.lower() == ".zip":
            upload_name = f"{display_name}.htz"
            mime = "application/zip"
            LOG.info("Uploading zip as HTML package %s (mime=%s)", upload_name, mime)
        else:
            upload_name = f"{display_name}{file_path.suffix.lower()}"

        with file_path.open("rb") as handle:
            files = {"files": (upload_name, handle, mime)}
            data = {"name": display_name}
            payload = self.request("POST", "/api/library", files=files, data=data)

        # Library upload returns 200 even on rejection; check embedded error.
        if isinstance(payload, dict):
            for item in payload.get("files") or []:
                if isinstance(item, dict) and item.get("error"):
                    err = str(item.get("error") or "")
                    if "already own media" in err.lower():
                        existing = self.find_media_by_name(display_name)
                        if existing is None:
                            # HTML packages are often stored under the .htz basename.
                            existing = self.find_media_by_name(Path(upload_name).stem)
                        if existing is not None:
                            LOG.info(
                                "Reusing existing mediaId=%s for %s (duplicate upload)",
                                existing,
                                display_name,
                            )
                            return existing
                    raise PipelineError(
                        f"Library rejected {upload_name}: {err} "
                        f"(type={item.get('type')}, size={item.get('size')})"
                    )

        media_id = _extract_id(payload, keys=("mediaId", "id"))
        if media_id is None:
            raise PipelineError(f"Could not parse mediaId from upload response: {payload}")
        LOG.info("Uploaded mediaId=%s name=%s", media_id, display_name)
        return media_id

    def create_layout(self, name: str, width: int = 1920, height: int = 1080) -> dict[str, Any]:
        LOG.info("Creating layout %s", name)
        payload = self.request(
            "POST",
            "/api/layout",
            data={"name": name, "resolutionId": _resolution_id_for(self, width, height)},
        )
        layout = payload[0] if isinstance(payload, list) else payload
        return layout

    def checkout_layout(self, layout_id: int) -> dict[str, Any]:
        LOG.info("Checking out layoutId=%s", layout_id)
        payload = self.request("PUT", f"/api/layout/checkout/{layout_id}")
        return payload[0] if isinstance(payload, list) else payload

    def publish_layout(self, layout_id: int) -> dict[str, Any]:
        LOG.info("Publishing layoutId=%s", layout_id)
        payload = self.request("PUT", f"/api/layout/publish/{layout_id}", data={"publishNow": 1})
        return payload[0] if isinstance(payload, list) else payload

    def get_layout(
        self,
        *,
        layout_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        params: dict[str, Any] = {"embed": "regions,playlists,widgets,regionPlaylists"}
        if layout_id is not None:
            params["layoutId"] = layout_id
        if parent_id is not None:
            params["parentId"] = parent_id
        details = self.request("GET", "/api/layout", params=params)
        if isinstance(details, list) and details:
            return details[0]
        if isinstance(details, dict):
            return details
        return None

    def resolve_draft_layout(self, published_layout_id: int) -> dict[str, Any]:
        """Return the editable draft for a layout created/returned by the API.

        Xibo's layout add returns the parent id; the editable draft is queried via
        ``parentId``. If already a draft, the same record is returned.
        """
        draft = self.get_layout(parent_id=published_layout_id)
        if draft:
            LOG.info(
                "Resolved draft layoutId=%s for parentId=%s",
                draft.get("layoutId"),
                published_layout_id,
            )
            return draft

        # Maybe the id we have is already the draft.
        current = self.get_layout(layout_id=published_layout_id)
        if current and (
            str(current.get("publishedStatus") or "").lower() == "draft"
            or current.get("publishedStatusId") == 2
        ):
            return current

        try:
            return self.checkout_layout(published_layout_id)
        except PipelineError as exc:
            # Already checked out — re-query by parentId once more.
            draft = self.get_layout(parent_id=published_layout_id)
            if draft:
                return draft
            raise PipelineError(
                f"Unable to resolve draft layout for layoutId={published_layout_id}: {exc}"
            ) from exc

    def add_region(
        self,
        layout_id: int,
        *,
        width: int = 1920,
        height: int = 1080,
        top: int = 0,
        left: int = 0,
        name: Optional[str] = None,
        z_index: Optional[int] = None,
    ) -> dict[str, Any]:
        LOG.info(
            "Adding region %s to draft layoutId=%s (%sx%s @ %s,%s)",
            name or "(unnamed)",
            layout_id,
            width,
            height,
            left,
            top,
        )
        data: dict[str, Any] = {
            "width": width,
            "height": height,
            "top": top,
            "left": left,
        }
        if name:
            data["name"] = name
        if z_index is not None:
            data["zIndex"] = z_index
        payload = self.request("POST", f"/api/region/{layout_id}", data=data)
        return payload[0] if isinstance(payload, list) else payload

    def delete_region(self, region_id: int) -> None:
        LOG.info("Deleting regionId=%s", region_id)
        self.request("DELETE", f"/api/region/{region_id}")

    def edit_layout(
        self,
        layout_id: int,
        *,
        name: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if duration is not None:
            data["duration"] = int(duration)
        if not data:
            return {}
        LOG.info("Editing layoutId=%s %s", layout_id, data)
        payload = self.request("PUT", f"/api/layout/{layout_id}", data=data)
        return payload[0] if isinstance(payload, list) else (payload or {})

    def _playlist_id_from_region(self, region: dict[str, Any]) -> Optional[int]:
        playlists = region.get("regionPlaylist") or region.get("playlists") or []
        if isinstance(playlists, dict):
            value = playlists.get("playlistId") or playlists.get("playlistid")
            return int(value) if value is not None else None
        if isinstance(playlists, list) and playlists:
            value = playlists[0].get("playlistId") or playlists[0].get("playlistid")
            return int(value) if value is not None else None
        value = region.get("playlistId") or region.get("playlistid")
        return int(value) if value is not None else None

    def _region_id(self, region: dict[str, Any]) -> Optional[int]:
        value = region.get("regionId") or region.get("regionid")
        return int(value) if value is not None else None

    def clear_regions(self, draft_layout_id: int) -> None:
        draft = self.get_layout(layout_id=draft_layout_id)
        if not draft:
            return
        for region in draft.get("regions") or []:
            rid = self._region_id(region)
            if rid is not None:
                try:
                    self.delete_region(rid)
                except PipelineError as exc:
                    LOG.warning("Failed to delete regionId=%s: %s", rid, exc)

    def assign_media_to_playlist(
        self,
        playlist_id: int,
        media_id: int,
        *,
        duration: int,
    ) -> Any:
        LOG.info(
            "Assigning mediaId=%s to playlistId=%s duration=%ss",
            media_id,
            playlist_id,
            duration,
        )
        return self.request(
            "POST",
            f"/api/playlist/library/assign/{playlist_id}",
            data=[("media[]", str(media_id)), ("duration", str(int(duration)))],
        )

    def add_widget(self, widget_type: str, playlist_id: int) -> dict[str, Any]:
        LOG.info("Adding widget type=%s to playlistId=%s", widget_type, playlist_id)
        payload = self.request("POST", f"/api/playlist/widget/{widget_type}/{playlist_id}")
        widget = payload[0] if isinstance(payload, list) else payload
        if not isinstance(widget, dict):
            raise PipelineError(f"Unexpected widget add response: {payload}")
        return widget

    def edit_widget(self, widget_id: int, data: dict[str, Any] | list[tuple[str, str]]) -> Any:
        LOG.debug("Editing widgetId=%s", widget_id)
        return self.request("PUT", f"/api/playlist/widget/{widget_id}", data=data)

    def add_spacer_widget(self, playlist_id: int, duration: int) -> int:
        duration = max(1, int(duration))
        widget = self.add_widget("spacer", playlist_id)
        widget_id = int(widget.get("widgetId") or widget.get("widgetid") or 0)
        if not widget_id:
            raise PipelineError(f"spacer widget missing id: {widget}")
        self.edit_widget(
            widget_id,
            {"duration": duration, "useDuration": 1},
        )
        return widget_id

    def add_text_widget(
        self,
        playlist_id: int,
        text: str,
        duration: int,
        *,
        effect: str = "none",
    ) -> int:
        duration = max(1, int(duration))
        widget: Optional[dict[str, Any]] = None
        last_error: Optional[Exception] = None
        for path, data in (
            (f"/api/playlist/widget/text/{playlist_id}", None),
            (f"/api/playlist/widget/{playlist_id}", {"type": "text"}),
        ):
            try:
                if data is None:
                    payload = self.request("POST", path)
                else:
                    payload = self.request("POST", path, data=data)
                candidate = payload[0] if isinstance(payload, list) else payload
                if isinstance(candidate, dict):
                    widget = candidate
                    break
            except PipelineError as exc:
                last_error = exc
                LOG.debug("text widget add via %s failed: %s", path, exc)
        if widget is None:
            raise PipelineError(f"Unable to add text widget: {last_error}")

        widget_id = int(widget.get("widgetId") or widget.get("widgetid") or 0)
        if not widget_id:
            raise PipelineError(f"text widget missing id: {widget}")

        effect_key = (effect or "none").strip()
        plain = " ".join(text.split())
        # Paint the band inside the text widget so background and glyphs share
        # one box. Separate scrim images get aspect-fitted by the player and
        # drift away from the text.
        band_bg = "#0A2A3A"
        if effect_key == "tickerScroll":
            html = (
                "<div style=\"font-family:'Source Sans 3',Segoe UI,sans-serif;"
                "font-size:34px;line-height:1.2;font-weight:600;color:#E8F4F8;"
                f"background:{band_bg};padding:28px 32px;box-sizing:border-box;"
                "width:100%;height:100%;white-space:nowrap;\">"
                f"{_escape_html(plain)}</div>"
            )
            edit_payload: dict[str, Any] = {
                "duration": duration,
                "useDuration": 1,
                "text": html,
                "ta_text": html,
                # Native player marquee — CSS @keyframes do not run in Xibo text.
                "effect": "marqueeLeft",
                "speed": 1,
            }
        else:
            html = (
                "<div style=\"font-family:'Source Sans 3',Segoe UI,sans-serif;"
                "font-size:36px;line-height:1.35;font-weight:600;color:#F4F8FC;"
                f"background:{band_bg};padding:24px 28px;box-sizing:border-box;"
                "width:100%;height:100%;white-space:pre-wrap;\">"
                f"{_escape_html(text)}</div>"
            )
            edit_payload = {
                "duration": duration,
                "useDuration": 1,
                "text": html,
                "ta_text": html,
                "effect": "noTransition",
                "speed": 1,
            }
        try:
            self.edit_widget(widget_id, edit_payload)
        except PipelineError as exc:
            LOG.warning("text widget edit with HTML/effect failed (%s); retrying plain", exc)
            fallback = {
                "duration": duration,
                "useDuration": 1,
                "text": plain if effect_key == "tickerScroll" else text,
            }
            if effect_key == "tickerScroll":
                fallback["effect"] = "marqueeLeft"
                fallback["speed"] = 1
            self.edit_widget(widget_id, fallback)
        return widget_id

    def ensure_media_on_layout(
        self,
        published_layout_id: int,
        media_id: int,
        *,
        duration: int = 15,
        width: int = 1920,
        height: int = 1080,
    ) -> dict[str, Any]:
        """Ensure draft has a region + assigned library media; return draft layout."""
        draft = self.resolve_draft_layout(published_layout_id)
        draft_layout_id = int(draft.get("layoutId") or draft.get("layoutid") or 0)
        regions = draft.get("regions") or []
        if not regions:
            self.add_region(draft_layout_id, width=width, height=height)
            draft = self.get_layout(layout_id=draft_layout_id) or self.resolve_draft_layout(
                published_layout_id
            )
            draft_layout_id = int(draft.get("layoutId") or draft.get("layoutid") or draft_layout_id)
            regions = draft.get("regions") or []

        if not regions:
            raise PipelineError(f"Draft layout {draft_layout_id} still has no regions after add")

        playlist_id = self._playlist_id_from_region(regions[0])
        if not playlist_id:
            draft = self.get_layout(layout_id=draft_layout_id) or draft
            regions = draft.get("regions") or regions
            playlist_id = self._playlist_id_from_region(regions[0]) if regions else None
        if not playlist_id:
            raise PipelineError(f"Could not resolve playlistId on layout {draft_layout_id}")

        self.assign_media_to_playlist(playlist_id, media_id, duration=duration)
        return draft

    def find_display(self, display_name: str) -> Optional[dict[str, Any]]:
        payload = self.request("GET", "/api/display", params={"display": display_name})
        if isinstance(payload, list):
            for item in payload:
                if str(item.get("display") or "").lower() == display_name.lower():
                    return item
            return payload[0] if payload else None
        return None

    def list_displays(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "/api/display")
        return payload if isinstance(payload, list) else []

    def wait_for_display(self, display_name: str, timeout_seconds: int = 180) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        LOG.info("Waiting for display registration: %s", display_name)
        while time.time() < deadline:
            display = self.find_display(display_name)
            if display:
                LOG.info(
                    "Found displayId=%s displayGroupId=%s licensed=%s",
                    display.get("displayId"),
                    display.get("displayGroupId"),
                    display.get("licensed"),
                )
                return display
            known = self.list_displays()
            if known:
                names = [str(d.get("display")) for d in known]
                LOG.info("Displays present (%s): %s", len(names), names)
                # Accept hardware-key style names if exact display name not yet set.
                for item in known:
                    if hardware_key_matches(item, display_name):
                        return item
            time.sleep(5)
        # Final dump of player logs to aid diagnosis.
        docker_exec(
            PLAYER_CONTAINER,
            ["bash", "-lc", "tail -n 80 /artifacts/player.log 2>/dev/null || true"],
            check=False,
        )
        raise PipelineError(f"Display {display_name!r} did not register within {timeout_seconds}s")

    def register_display_via_xmds(
        self,
        *,
        server_key: str,
        hardware_key: str,
        display_name: str,
    ) -> None:
        """Bootstrap a display row via XMDS only when it does not exist yet.

        Important: Soap5 overwrites ``xmrChannel`` on every READY RegisterDisplay.
        A register call without XMR fields clears the channel and breaks collectNow.
        Once the Linux player has registered, never re-register from the pipeline.
        """
        existing = self.find_display(display_name)
        if existing is None:
            # Hardware-key match (player may use default name "Display" briefly).
            try:
                payload = self.request("GET", "/api/display")
                items = payload if isinstance(payload, list) else []
            except PipelineError:
                items = []
            for item in items:
                if hardware_key_matches(item, display_name):
                    existing = item
                    break
        if existing is not None:
            LOG.info(
                "Display already present (displayId=%s); skipping pipeline XMDS register "
                "to preserve xmrChannel",
                existing.get("displayId"),
            )
            return

        LOG.info("Bootstrapping display via XMDS hardwareKey=%s", hardware_key)
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:x="urn:xmds.xibo.org.uk">
  <soapenv:Header/>
  <soapenv:Body>
    <x:RegisterDisplay>
      <serverKey>{server_key}</serverKey>
      <hardwareKey>{hardware_key}</hardwareKey>
      <displayName>{display_name}</displayName>
      <clientType>linux</clientType>
      <clientVersion>1.8-R6</clientVersion>
      <clientCode>6</clientCode>
      <operatingSystem>Linux</operatingSystem>
      <macAddress>00:11:22:33:44:55</macAddress>
      <xmrChannel>qa-bootstrap-channel</xmrChannel>
      <xmrPubKey></xmrPubKey>
    </x:RegisterDisplay>
  </soapenv:Body>
</soapenv:Envelope>
"""
        # Try common XMDS versions used by Linux player builds.
        last_error = "unknown"
        for version in ("5", "4", "3"):
            try:
                response = self.session.post(
                    self._url(f"/xmds.php?v={version}"),
                    data=body,
                    headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "RegisterDisplay"},
                    timeout=self.timeout,
                )
                if response.status_code < 400 and "fault" not in response.text.lower():
                    LOG.info("XMDS RegisterDisplay accepted via v=%s", version)
                    return
                last_error = f"v={version} HTTP {response.status_code}: {response.text[:300]}"
            except requests.RequestException as exc:
                last_error = str(exc)
        raise PipelineError(f"XMDS RegisterDisplay failed: {last_error}")

    def authorise_display(self, display: dict[str, Any], *, hardware_key: str) -> None:
        display_id = int(display["displayId"])
        LOG.info("Authorising displayId=%s", display_id)
        # Prefer the dedicated authorise route (avoids full-form PUT validation).
        for path in (
            f"/api/display/authorise/{display_id}",
            f"/api/display/{display_id}/authorise",
        ):
            try:
                self.request("PUT", path)
                LOG.info("Authorised via %s", path)
                return
            except PipelineError as exc:
                LOG.debug("authorise via %s failed: %s", path, exc)
        LOG.warning("dedicated authorise routes failed; falling back to edit PUT")

        payload = self._display_edit_payload(display, hardware_key=hardware_key, licensed=1)
        try:
            self.request("PUT", f"/api/display/{display_id}", data=payload)
            return
        except PipelineError as exc:
            LOG.warning("display edit PUT failed (%s); authorising via MySQL", exc)
            mysql_exec(
                f"UPDATE `display` SET licensed=1 WHERE displayId={display_id};",
                check=True,
            )

    def set_default_layout(
        self,
        display: dict[str, Any],
        layout_id: int,
        *,
        hardware_key: str,
    ) -> None:
        display_id = int(display["displayId"])
        LOG.info("Setting default layoutId=%s on displayId=%s", layout_id, display_id)
        payload = self._display_edit_payload(
            display,
            hardware_key=hardware_key,
            licensed=1,
            defaultLayoutId=layout_id,
        )
        try:
            self.request("PUT", f"/api/display/{display_id}", data=payload)
            return
        except PipelineError as exc:
            LOG.warning("defaultLayout PUT failed (%s); updating via MySQL", exc)
            mysql_exec(
                "UPDATE `display` SET licensed=1, "
                f"defaultLayoutId={int(layout_id)} WHERE displayId={display_id};",
                check=True,
            )

    @staticmethod
    def _display_edit_payload(
        display: dict[str, Any],
        *,
        hardware_key: str,
        licensed: int = 1,
        defaultLayoutId: Optional[int] = None,
    ) -> dict[str, Any]:
        """Build a CMS 4-compatible display edit body from an existing record."""
        name = str(display.get("display") or display.get("displayName") or "qa-kiosk-01")
        license_key = str(
            display.get("license")
            or display.get("hardwareKey")
            or hardware_key
        )
        payload: dict[str, Any] = {
            "display": name,
            "license": license_key,
            "licensed": licensed,
        }
        layout = defaultLayoutId if defaultLayoutId is not None else display.get("defaultLayoutId")
        if layout not in (None, "", 0, "0"):
            payload["defaultLayoutId"] = int(layout)

        # Copy through optional profile/type fields when present so PUT validation passes.
        for key in (
            "displayProfileId",
            "displayTypeId",
            "venueTypeId",
            "languagesId",
            "folderId",
            "xmrChannel",
            "xmrPubKey",
            "emailAddress",
            "wakeOnLanEnabled",
            "wakeOnLanTime",
            "broadCastAddress",
            "secureOn",
            "cidr",
            "latitude",
            "longitude",
            "timeZone",
            "incidentEmail",
        ):
            value = display.get(key)
            if value not in (None, ""):
                payload[key] = value
        return payload

    def schedule_layout(self, display_group_id: int, campaign_id: int, event_name: str) -> int:
        # CMS 4 expects datetime strings (Y-m-d H:i:s), not unix timestamps.
        now = datetime.now(timezone.utc)
        from_dt = (now - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
        to_dt = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        payload = self.request(
            "POST",
            "/api/schedule",
            data={
                "eventTypeId": 1,  # Layout (campaignId refers to the layout campaign)
                "campaignId": campaign_id,
                "displayGroupIds[]": display_group_id,
                "fromDt": from_dt,
                "toDt": to_dt,
                "isPriority": 1,
                "displayOrder": 1,
                "name": event_name,
            },
        )
        event_id = _extract_id(payload, keys=("eventId", "id"))
        if event_id is None:
            raise PipelineError(f"Could not parse schedule event id: {payload}")
        LOG.info("Scheduled eventId=%s", event_id)
        return event_id

    def clear_schedule_for_display_group(self, display_group_id: int) -> int:
        """Remove prior schedule events so the player does not paint stale HTML layouts.

        Keep-stack QA runs accumulate overlapping priority events; the Linux player
        then starts an old region set and SIGSEGVs in RegionImpl::start() when a
        region has an empty media list (e.g. failed html-package).
        """
        deleted = 0
        # Prefer API list; fall back to MySQL for CMS builds with awkward schedule filters.
        event_ids: list[int] = []
        try:
            now = datetime.now(timezone.utc)
            frm = int((now - timedelta(days=30)).timestamp() * 1000)
            to = int((now + timedelta(days=30)).timestamp() * 1000)
            data = self.request(
                "GET",
                "/api/schedule/data/events",
                params={
                    "displayGroupIds[]": display_group_id,
                    "from": frm,
                    "to": to,
                },
            )
            rows = data if isinstance(data, list) else (data.get("data") or data.get("result") or [])
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                event = row.get("event") if isinstance(row.get("event"), dict) else row
                eid = _extract_id(event, keys=("eventId", "id"))
                if eid is None:
                    eid = _extract_id(row, keys=("eventId", "id"))
                if eid is not None:
                    event_ids.append(int(eid))
        except PipelineError as exc:
            LOG.warning("Schedule API list failed (%s); using MySQL", exc)

        if not event_ids:
            sql = (
                "SELECT l.eventId FROM lkscheduledisplaygroup l "
                f"WHERE l.displayGroupId={int(display_group_id)}"
            )
            raw = mysql_scalar_multi(sql)
            event_ids = [int(x) for x in raw if str(x).isdigit()]

        for eid in sorted(set(event_ids)):
            try:
                self.request("DELETE", f"/api/schedule/{eid}")
                deleted += 1
            except PipelineError as exc:
                LOG.warning("Could not delete schedule eventId=%s: %s", eid, exc)
                # Last resort: direct SQL (QA ephemeral CMS only).
                mysql_exec(
                    "DELETE FROM schedulereminder WHERE eventId="
                    f"{eid}; DELETE FROM scheduleexclusions WHERE eventId={eid}; "
                    f"DELETE FROM lkscheduledisplaygroup WHERE eventId={eid}; "
                    f"DELETE FROM schedule WHERE eventId={eid};",
                    check=False,
                )
                deleted += 1
        LOG.info(
            "Cleared %s schedule event(s) for displayGroupId=%s",
            deleted,
            display_group_id,
        )
        return deleted

    def change_layout_now(
        self,
        display_group_id: int,
        layout_id: int,
        duration: int = 60,
        *,
        campaign_id: Optional[int] = None,
    ) -> bool:
        """Push an immediate layout change over XMR.

        CMS 4 ``changeLayout`` resolves via ``layoutFactory.getById(layoutId)`` or a
        layout-specific ``campaignId``. Prefer campaignId when available — some
        published parents 404 by layoutId alone depending on draft/publish state.
        """
        data: dict[str, Any] = {
            "duration": duration,
            "downloadRequired": 1,
            "changeMode": "queue",
        }
        if campaign_id:
            LOG.info(
                "XMR changeLayout campaignId=%s -> displayGroupId=%s",
                campaign_id,
                display_group_id,
            )
            data["campaignId"] = int(campaign_id)
        else:
            LOG.info(
                "XMR changeLayout layoutId=%s -> displayGroupId=%s",
                layout_id,
                display_group_id,
            )
            data["layoutId"] = int(layout_id)
        try:
            self.request(
                "POST",
                f"/api/displaygroup/{display_group_id}/action/changeLayout",
                data=data,
            )
            return True
        except PipelineError as exc:
            if campaign_id and layout_id:
                LOG.warning("changeLayout via campaignId failed (%s); retrying layoutId", exc)
                try:
                    self.request(
                        "POST",
                        f"/api/displaygroup/{display_group_id}/action/changeLayout",
                        data={
                            "layoutId": int(layout_id),
                            "duration": duration,
                            "downloadRequired": 1,
                            "changeMode": "queue",
                        },
                    )
                    return True
                except PipelineError as exc2:
                    LOG.warning("changeLayout skipped (XMR not ready): %s", exc2)
                    return False
            LOG.warning("changeLayout skipped (XMR not ready): %s", exc)
            return False

    def collect_now(self, display_group_id: int) -> bool:
        LOG.info("XMR collectNow displayGroupId=%s", display_group_id)
        try:
            self.request("POST", f"/api/displaygroup/{display_group_id}/action/collectNow")
            return True
        except PipelineError as exc:
            LOG.warning("collectNow skipped (XMR not ready): %s", exc)
            return False


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _mime_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".zip": "application/zip",
        ".htz": "application/zip",
        ".html": "text/html",
        ".htm": "text/html",
    }.get(suffix, "application/octet-stream")


def _extract_id(payload: Any, keys: tuple[str, ...]) -> Optional[int]:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if isinstance(payload, dict):
        # library upload often nests under files / data
        for container_key in ("files", "data", "record"):
            nested = payload.get(container_key)
            if nested:
                found = _extract_id(nested, keys)
                if found is not None:
                    return found
        for key in keys:
            if key in payload and payload[key] is not None:
                return int(payload[key])
    return None


def _resolution_id_for(client: XiboClient, width: int, height: int) -> int:
    try:
        resolutions = client.request("GET", "/api/resolution", params={"width": width, "height": height})
        if isinstance(resolutions, list) and resolutions:
            return int(resolutions[0]["resolutionId"])
    except PipelineError:
        pass
    # Common default HD resolutionId on fresh CMS installs is often 1 or 9; create if needed.
    try:
        created = client.request(
            "POST",
            "/api/resolution",
            data={"resolution": f"QA {width}x{height}", "width": width, "height": height},
        )
        rid = _extract_id(created, keys=("resolutionId", "id"))
        if rid is not None:
            return rid
    except PipelineError:
        pass
    return 1


def _extract_html_value(html: str, field_name: str) -> Optional[str]:
    marker = f'name="{field_name}"'
    idx = html.find(marker)
    if idx < 0:
        return None
    chunk = html[idx : idx + 240]
    if 'value="' not in chunk:
        return None
    return chunk.split('value="', 1)[1].split('"', 1)[0]


def mysql_exec(sql: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    password = os.environ.get("MYSQL_PASSWORD", "xiboQaMysqlPass16")
    cmd = [
        "docker",
        "exec",
        "xibo-qa-cms-db",
        "mysql",
        "-ucms",
        f"-p{password}",
        "cms",
        "-e",
        sql,
    ]
    return run_cmd(cmd, check=check)


def mysql_scalar(sql: str) -> Optional[str]:
    """Run a SQL statement expected to return a single scalar value."""
    password = os.environ.get("MYSQL_PASSWORD", "xiboQaMysqlPass16")
    cmd = [
        "docker",
        "exec",
        "xibo-qa-cms-db",
        "mysql",
        "-N",
        "-B",
        "-ucms",
        f"-p{password}",
        "cms",
        "-e",
        sql,
    ]
    result = run_cmd(cmd, check=False)
    if result.returncode != 0:
        LOG.debug("mysql_scalar failed: %s", (result.stderr or "").strip())
        return None
    value = (result.stdout or "").strip().splitlines()
    if not value:
        return None
    # mysql may emit password warnings on stderr only; stdout is the value.
    candidate = value[-1].strip()
    return candidate or None


def mysql_scalar_multi(sql: str) -> list[str]:
    """Run SQL expected to return one scalar per result row."""
    password = os.environ.get("MYSQL_PASSWORD", "xiboQaMysqlPass16")
    cmd = [
        "docker",
        "exec",
        "xibo-qa-cms-db",
        "mysql",
        "-N",
        "-B",
        "-ucms",
        f"-p{password}",
        "cms",
        "-e",
        sql,
    ]
    result = run_cmd(cmd, check=False)
    if result.returncode != 0:
        LOG.debug("mysql_scalar_multi failed: %s", (result.stderr or "").strip())
        return []
    return [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]


def oauth_schema_ready() -> bool:
    """True when the ephemeral CMS DB has finished creating OAuth tables."""
    result = mysql_exec("SHOW TABLES LIKE 'oauth_clients';", check=False)
    if result.returncode != 0:
        return False
    return "oauth_clients" in (result.stdout or "")


def seed_oauth_client_mysql(client_id: str, client_secret: str, name: str) -> None:
    """Insert a client_credentials OAuth client directly (ephemeral CMS only).

    Mirrors Xibo's Cypress CI seeding approach.
    """
    # IDs/secrets are hex-only to keep SQL quoting simple and safe.
    if not re.fullmatch(r"[0-9a-fA-F]+", client_id):
        raise PipelineError("client_id must be hex for MySQL seeding")
    if not re.fullmatch(r"[0-9a-fA-F]+", client_secret):
        raise PipelineError("client_secret must be hex for MySQL seeding")
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]

    # Wait briefly for first-boot migrations if needed.
    deadline = time.time() + 120
    while time.time() < deadline and not oauth_schema_ready():
        time.sleep(3)
    if not oauth_schema_ready():
        raise PipelineError("oauth_clients table never became available")

    sql = f"""
    INSERT INTO oauth_clients (id, secret, name, userId, authCode, clientCredentials)
    VALUES ('{client_id}', '{client_secret}', '{safe_name}', 1, 0, 1)
    ON DUPLICATE KEY UPDATE
      secret=VALUES(secret),
      name=VALUES(name),
      authCode=0,
      clientCredentials=1;
    INSERT INTO oauth_client_scopes (clientId, scopeId)
    VALUES ('{client_id}', 'all')
    ON DUPLICATE KEY UPDATE scopeId=VALUES(scopeId);
    """
    result = mysql_exec(sql, check=False)
    if result.returncode != 0:
        raise PipelineError(
            "Failed to seed OAuth client via MySQL. "
            f"stderr={(result.stderr or '').strip()} stdout={(result.stdout or '').strip()}"
        )
    LOG.info("Seeded oauth client %s in MySQL", client_id)


def configure_xmr_settings(
    *,
    private_address: str = "http://cms-xmr:8081",
    public_address: str = "tcp://cms-xmr:9505",
) -> None:
    """Point CMS at the compose-network XMR container (private + public sockets).

    CMS 4.2+ talks to XMR over HTTP (``XMR_ADDRESS`` = ``http://cms-xmr:8081``).
    Legacy Linux players still subscribe on ZeroMQ (``XMR_PUB_ADDRESS`` /
    player ``xmrNetworkAddress`` = ``tcp://cms-xmr:9505``). Fresh CMS defaults
    the public address to ``tcp://cms.example.org:9505``, which qa-net cannot
    resolve — seed Docker-correct values and flush memcached.
    """
    # Guard against SQL injection — fixed http(s)/tcp host:port forms only.
    private_ok = re.fullmatch(r"https?://[A-Za-z0-9._-]+:\d+", private_address)
    public_ok = re.fullmatch(r"tcp://[A-Za-z0-9._-]+:\d+", public_address)
    if not private_ok:
        raise PipelineError(f"Invalid XMR private address: {private_address!r}")
    if not public_ok:
        raise PipelineError(f"Invalid XMR public address: {public_address!r}")

    deadline = time.time() + 120
    while time.time() < deadline:
        if mysql_scalar("SELECT `setting` FROM `setting` WHERE `setting`='XMR_ADDRESS' LIMIT 1"):
            break
        time.sleep(3)
    else:
        raise PipelineError("CMS setting table never exposed XMR_ADDRESS")

    sql = f"""
    UPDATE `setting` SET `value`='{private_address}', userSee=0, userChange=0
      WHERE `setting`='XMR_ADDRESS';
    UPDATE `setting` SET `value`='{public_address}'
      WHERE `setting`='XMR_PUB_ADDRESS';
    """
    result = mysql_exec(sql, check=False)
    if result.returncode != 0:
        raise PipelineError(
            "Failed to configure XMR settings via MySQL. "
            f"stderr={(result.stderr or '').strip()} stdout={(result.stdout or '').strip()}"
        )

    # Drop cached settings so cms-web reads the new addresses.
    # Restart is more reliable than nc on the minimal memcached image.
    flush = run_cmd(
        ["docker", "restart", "xibo-qa-cms-memcached"],
        check=False,
    )
    if flush.returncode == 0:
        time.sleep(2)
    LOG.info(
        "Configured XMR private=%s public=%s (memcache_restart_rc=%s)",
        private_address,
        public_address,
        flush.returncode,
    )


# ---------------------------------------------------------------------------
# Docker / capture helpers
# ---------------------------------------------------------------------------


def hardware_key_matches(display: dict[str, Any], display_name: str) -> bool:
    name = str(display.get("display") or "").lower()
    if name == display_name.lower():
        return True
    # Some registrations use the hardware key as the initial display name.
    hw = os.environ.get("XIBO_HARDWARE_KEY", "qa-kiosk-01-hw").lower()
    return name == hw or str(display.get("license") or "").lower() == hw


TIMELINE_PREVIEW_DIR = PLAYER_RUNTIME_DIR / "timeline-preview"


def prepare_timeline_preview(settings: "Settings") -> Optional[dict[str, Any]]:
    """Render exhibits/<slug>/layouts/timeline.yaml into the player bind mount.

    Returns metadata when a timeline exists; None when the exhibit has no
    timeline (caller falls back to static feh preview).
    """
    timeline_path = EXHIBITS_DIR / settings.exhibit_slug / "layouts" / "timeline.yaml"
    if not timeline_path.is_file():
        LOG.info("No timeline.yaml for exhibit=%s; static preview only", settings.exhibit_slug)
        return None

    # Import lazily so --verify-only does not require the renderer package path.
    sys.path.insert(0, str(QA_DIR / "timeline_preview"))
    try:
        from render_timeline import render_exhibit  # type: ignore
    except ImportError as exc:
        raise PipelineError(
            "Failed to import timeline_preview.render_timeline (is PyYAML installed?)"
        ) from exc

    meta = render_exhibit(
        settings.exhibit_slug,
        out_dir=TIMELINE_PREVIEW_DIR,
        record_duration=settings.record_duration,
        show_hud=True,
    )
    LOG.info(
        "Rendered timeline preview renderer=timeline-preview out=%s duration=%ss",
        meta.get("out_dir"),
        meta.get("record_duration"),
    )
    return meta


def wait_for_player_running(*, timeout_seconds: int = 90, stable_seconds: int = 8) -> None:
    """Wait until the kiosk-player container stays Running (not restarting)."""
    deadline = time.time() + timeout_seconds
    last_status = ""
    stable_since: Optional[float] = None
    while time.time() < deadline:
        probe = run_cmd(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Status}}|{{.State.Running}}|{{.State.Restarting}}",
                PLAYER_CONTAINER,
            ],
            check=False,
        )
        last_status = (probe.stdout or "").strip()
        parts = last_status.split("|")
        status = parts[0] if parts else ""
        running = parts[1].lower() == "true" if len(parts) > 1 else False
        restarting = parts[2].lower() == "true" if len(parts) > 2 else False
        if running and not restarting and status == "running":
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= stable_seconds:
                LOG.info("Player container is stable (%s)", last_status)
                return
        else:
            stable_since = None
            LOG.debug("Waiting for player container: %s", last_status)
        time.sleep(2)
    logs = run_cmd(["docker", "logs", "--tail", "120", PLAYER_CONTAINER], check=False)
    raise PipelineError(
        f"Player container not stable after {timeout_seconds}s (last={last_status}).\n"
        f"stdout={(logs.stdout or '')[-2000:]}\nstderr={(logs.stderr or '')[-1000:]}"
    )


def player_process_alive() -> bool:
    """True when the Xibo player binary is running inside the container (not just Xvfb).

    Uses ``pgrep -x player`` only — a ``-f`` path match false-positives on the
    docker-exec shell that contains the path in its argv.
    """
    probe = docker_exec(
        PLAYER_CONTAINER,
        ["bash", "-lc", "pgrep -x player >/dev/null 2>&1"],
        check=False,
    )
    return probe.returncode == 0


def wait_for_player_process_alive(
    *,
    timeout_seconds: int = 60,
    stable_seconds: int = 5,
    poll_seconds: float = 1.0,
) -> None:
    """Wait until the player process stays up long enough to paint before scrot.

    Avoids capturing a black Xvfb frame while the supervisor is between crashes
    or has not yet relaunched after RegionImpl paint failures.
    """
    deadline = time.time() + timeout_seconds
    alive_since: Optional[float] = None
    while time.time() < deadline:
        if player_process_alive():
            if alive_since is None:
                alive_since = time.time()
                LOG.info("Player process detected; waiting %ss for paint settle", stable_seconds)
            elif time.time() - alive_since >= stable_seconds:
                LOG.info("Player process stable for %ss", stable_seconds)
                return
        else:
            if alive_since is not None:
                LOG.warning("Player process died during paint settle; waiting for relaunch")
            alive_since = None
        time.sleep(poll_seconds)
    # Dump recent player log for diagnosis.
    logs = docker_exec(
        PLAYER_CONTAINER,
        ["bash", "-lc", "tail -n 60 /artifacts/player.log 2>/dev/null || true"],
        check=False,
    )
    raise PipelineError(
        f"Xibo player process not stable for {stable_seconds}s within {timeout_seconds}s.\n"
        f"player.log tail:\n{(logs.stdout or '')[-2000:]}"
    )


def provision_player_cms_config(
    *,
    settings: "Settings",
    cms_url: str,
    cms_key: str,
    display_name: str,
    hardware_key: str,
    recreate: bool = True,
) -> None:
    """Write player CMS config on the host bind mount and optionally recreate the player.

    Avoids ``docker exec`` into a possibly-crashed container (common while the
    snap player is still settling under Xvfb).
    """
    runtime = PLAYER_RUNTIME_DIR
    snap_common = runtime / "snap-common"
    snap_common.mkdir(parents=True, exist_ok=True)

    # Native volume inside the container (see docker-compose XIBO_LOCAL_LIBRARY).
    local_library = "/data/xibo-library"
    xmr_address = os.environ.get("XIBO_XMR_ADDRESS", "tcp://cms-xmr:9505").strip()

    cms_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<settings version="2">\n'
        f"  <cmsAddress>{cms_url}</cmsAddress>\n"
        f"  <key>{cms_key}</key>\n"
        f"  <localLibrary>{local_library}</localLibrary>\n"
        f"  <displayId>{hardware_key}</displayId>\n"
        "</settings>\n"
    )
    player_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<settings version="2">\n'
        f"  <displayName>{display_name}</displayName>\n"
        "  <sizeX>1920</sizeX>\n"
        "  <sizeY>1080</sizeY>\n"
        "  <offsetX>0</offsetX>\n"
        "  <offsetY>0</offsetY>\n"
        # Snap 1.8-R6 PlayerSettings.hpp typo: loadField looks for offfsetY.
        "  <offfsetY>0</offfsetY>\n"
        "  <preventSleep>true</preventSleep>\n"
        "  <collectInterval>30</collectInterval>\n"
        "  <logLevel>debug</logLevel>\n"
        f"  <xmrNetworkAddress>{xmr_address}</xmrNetworkAddress>\n"
        "</settings>\n"
    )
    config_json = json.dumps(
        {
            "cmsAddress": cms_url,
            "cmsKey": cms_key,
            "displayName": display_name,
            "displayId": hardware_key,
            "localLibrary": local_library,
            "xmrNetworkAddress": xmr_address,
        },
        indent=2,
    )

    def _write_lf(path: Path, text: str) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    _write_lf(runtime / "cmsSettings.xml", cms_xml)
    _write_lf(snap_common / "cmsSettings.xml", cms_xml)
    _write_lf(runtime / "playerSettings.xml", player_xml)
    _write_lf(runtime / "config.json", config_json + "\n")

    # Stale XMDS cache on the Windows bind mount can claim media is present while the
    # native library volume is empty after `down -v`.
    for stale in ("cacheFile.xml", "schedule.xml", "requiredFiles.xml"):
        stale_path = runtime / stale
        if stale_path.exists():
            stale_path.unlink()
            LOG.info("Removed stale player cache file %s", stale_path.name)

    # Fallback still for optional feh preview mode.
    preview = runtime / "preview.png"
    if settings.media_path.is_file():
        shutil.copy2(settings.media_path, preview)
    elif not preview.is_file():
        ensure_fixture_image(DEFAULT_FIXTURE)
        shutil.copy2(DEFAULT_FIXTURE, preview)
    LOG.info(
        "Wrote player config under %s (localLibrary=%s key_len=%s)",
        runtime,
        local_library,
        len(cms_key),
    )

    # Last compose --env-file wins over config.env's empty XIBO_CMS_KEY=, so the
    # entrypoint always receives the live SERVER_KEY (not a stale bind-mount key).
    runtime_env = runtime / "compose.runtime.env"
    _write_lf(
        runtime_env,
        (
            f"XIBO_CMS_KEY={cms_key}\n"
            f"XIBO_DISPLAY_NAME={display_name}\n"
            f"XIBO_HARDWARE_KEY={hardware_key}\n"
            f"XIBO_CMS_INTERNAL_URL={cms_url}\n"
            f"XIBO_XMR_ADDRESS={xmr_address}\n"
            f"QA_USE_TIMELINE_PREVIEW={'1' if settings.preview_only else '0'}\n"
        ),
    )

    env = os.environ.copy()
    env["XIBO_CMS_KEY"] = cms_key
    env["XIBO_DISPLAY_NAME"] = display_name
    env["XIBO_HARDWARE_KEY"] = hardware_key
    env["XIBO_CMS_INTERNAL_URL"] = cms_url
    env["XIBO_LOCAL_LIBRARY"] = local_library
    env["XIBO_XMR_ADDRESS"] = xmr_address
    env["QA_USE_TIMELINE_PREVIEW"] = "1" if settings.preview_only else "0"
    if not recreate:
        LOG.info("Player config written; skipping container recreate (fast mode)")
        return

    up_args = ["up", "-d", "--no-deps", "--force-recreate", "kiosk-player"]
    if settings.rebuild_player:
        up_args.insert(2, "--build")
        LOG.info(
            "Recreating %s with --build (timeline_preview=%s library=%s xmr=%s)",
            PLAYER_CONTAINER,
            env["QA_USE_TIMELINE_PREVIEW"],
            local_library,
            xmr_address,
        )
    else:
        LOG.info(
            "Recreating %s without rebuild (timeline_preview=%s library=%s xmr=%s)",
            PLAYER_CONTAINER,
            env["QA_USE_TIMELINE_PREVIEW"],
            local_library,
            xmr_address,
        )
    run_cmd(
        compose_cmd(settings, *up_args),
        check=True,
        capture=False,
        env=env,
    )

    wait_for_player_running(timeout_seconds=60 if settings.fast else 90)


def restart_player_container(*, fast: bool = False) -> None:
    """Bounce the player process without rebuilding the image."""
    LOG.info("Restarting %s (no rebuild)", PLAYER_CONTAINER)
    run_cmd(["docker", "restart", PLAYER_CONTAINER], check=True, capture=False)
    wait_for_player_running(timeout_seconds=45 if fast else 90)


def stack_up(settings: Settings) -> None:
    LOG.info("Starting ephemeral compose stack")
    up_args = ["up", "-d"]
    if settings.rebuild_player:
        up_args.append("--build")
    run_cmd(compose_cmd(settings, *up_args), capture=False)


def stack_down(settings: Settings) -> None:
    LOG.info("Tearing down compose stack and volumes")
    run_cmd(
        compose_cmd(settings, "down", "-v", "--remove-orphans"),
        check=False,
        capture=False,
    )


def docker_exec(container: str, command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_cmd(["docker", "exec", container, *command], check=check)


def capture_framebuffer(
    artifact_dir: Path,
    *,
    record_duration: int = DEFAULT_RECORD_DURATION,
    also_video: bool = True,
    require_player_process: bool = True,
    paint_stable_seconds: int = 5,
) -> Path:
    """Grab a PNG (and optional MP4) from the player container DISPLAY :99."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    remote_png = f"/artifacts/frame-{stamp}.png"
    remote_mp4 = f"/artifacts/clip-{stamp}.mp4"
    local_png = artifact_dir / f"frame-{stamp}.png"
    local_mp4 = artifact_dir / f"clip-{stamp}.mp4"

    wait_for_player_running(timeout_seconds=60)
    if require_player_process:
        wait_for_player_process_alive(
            timeout_seconds=90,
            stable_seconds=paint_stable_seconds,
        )

    LOG.info("Capturing screenshot via scrot on DISPLAY=:99")
    last_error: Optional[Exception] = None
    for attempt in range(1, 6):
        try:
            if require_player_process and not player_process_alive():
                wait_for_player_process_alive(
                    timeout_seconds=45,
                    stable_seconds=max(3, paint_stable_seconds // 2),
                )
            docker_exec(
                PLAYER_CONTAINER,
                [
                    "bash",
                    "-lc",
                    f'export DISPLAY=:99; scrot -z "{remote_png}" || import -window root "{remote_png}"',
                ],
            )
            last_error = None
            break
        except PipelineError as exc:
            last_error = exc
            LOG.warning("Screenshot attempt %s/5 failed: %s", attempt, exc)
            wait_for_player_running(timeout_seconds=30)
            if require_player_process:
                wait_for_player_process_alive(timeout_seconds=45, stable_seconds=3)
            time.sleep(2)
    if last_error is not None:
        logs = run_cmd(["docker", "logs", "--tail", "80", PLAYER_CONTAINER], check=False)
        raise PipelineError(
            f"Screenshot capture failed after retries: {last_error}\n"
            f"player logs={(logs.stdout or '')[-2000:]}"
        )

    if also_video:
        LOG.info("Capturing %ss MP4 via ffmpeg x11grab", record_duration)
        docker_exec(
            PLAYER_CONTAINER,
            [
                "bash",
                "-lc",
                (
                    'export DISPLAY=:99; '
                    f'ffmpeg -y -f x11grab -video_size 1920x1080 -i :99 -t {int(record_duration)} '
                    f'-pix_fmt yuv420p "{remote_mp4}"'
                ),
            ],
            check=False,
        )

    # Copy out of the named volume via docker cp.
    run_cmd(["docker", "cp", f"{PLAYER_CONTAINER}:{remote_png}", to_docker_path(local_png)])
    if also_video:
        copied = run_cmd(
            ["docker", "cp", f"{PLAYER_CONTAINER}:{remote_mp4}", to_docker_path(local_mp4)],
            check=False,
        )
        if copied.returncode != 0:
            LOG.warning("MP4 capture not available")

    if not local_png.is_file():
        raise PipelineError("Failed to copy screenshot out of player container")
    LOG.info("Screenshot saved to %s", local_png)
    return local_png


def write_report(artifact_dir: Path, payload: dict[str, Any]) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "qa-report.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def wait_for_xmr_channel(
    client: XiboClient,
    display_name: str,
    *,
    timeout_seconds: int = 60,
) -> Optional[dict[str, Any]]:
    """Poll until the display reports an xmrChannel (or timeout)."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        display = client.find_display(display_name)
        if display and str(display.get("xmrChannel") or "").strip():
            channel = str(display.get("xmrChannel"))
            LOG.info(
                "Display %s has xmrChannel=%s…",
                display_name,
                channel[:16],
            )
            return display
        time.sleep(5)
    LOG.warning("Display %s still missing xmrChannel after %ss", display_name, timeout_seconds)
    return client.find_display(display_name)


def push_layout_to_display(
    client: XiboClient,
    *,
    display_name: str,
    display_group_id: int,
    layout_id: int,
    change_duration: int,
    fast: bool = False,
    campaign_id: Optional[int] = None,
) -> tuple[bool, bool]:
    """Send collectNow/changeLayout once xmrChannel is present."""
    first_wait = 10 if fast else 30
    wait_for_xmr_channel(client, display_name, timeout_seconds=first_wait)
    collected = client.collect_now(display_group_id)
    changed = client.change_layout_now(
        display_group_id,
        layout_id,
        duration=change_duration,
        campaign_id=campaign_id,
    )
    if collected and changed:
        return collected, changed
    if fast:
        return collected, changed
    time.sleep(5)
    wait_for_xmr_channel(client, display_name, timeout_seconds=15)
    if not collected:
        collected = client.collect_now(display_group_id)
    if not changed:
        changed = client.change_layout_now(
            display_group_id,
            layout_id,
            duration=change_duration,
            campaign_id=campaign_id,
        )
    return collected, changed


def player_library_file_count() -> int:
    probe = docker_exec(
        PLAYER_CONTAINER,
        [
            "bash",
            "-lc",
            (
                "lib=/data/xibo-library; "
                "count=$(find \"$lib\" -type f ! -name '.keep' 2>/dev/null | wc -l); "
                "echo \"library_files=$count\""
            ),
        ],
        check=False,
    )
    for line in (probe.stdout or "").splitlines():
        if line.startswith("library_files="):
            try:
                return int(line.split("=", 1)[1].strip())
            except ValueError:
                return 0
    return 0


def wait_for_player_library(
    *,
    min_library_files: int = 1,
    timeout_seconds: int = 90,
    poll_seconds: int = 5,
) -> int:
    """Poll until the player library has content (or timeout)."""
    deadline = time.time() + timeout_seconds
    count = 0
    while time.time() < deadline:
        count = player_library_file_count()
        LOG.info("Player library file count=%s (want >= %s)", count, min_library_files)
        if count >= min_library_files:
            return count
        time.sleep(poll_seconds)
    assert_player_has_content(min_library_files=min_library_files)
    return player_library_file_count()


def assert_player_has_content(*, min_library_files: int = 1) -> None:
    """Fail early if the player never collected CMS content into its library."""
    probe = docker_exec(
        PLAYER_CONTAINER,
        [
            "bash",
            "-lc",
            (
                "lib=/data/xibo-library; "
                "count=$(find \"$lib\" -type f ! -name '.keep' 2>/dev/null | wc -l); "
                "echo \"library_files=$count\"; "
                "ls -la \"$lib\" /var/lib/xibo-player/cmsSettings.xml "
                "/var/lib/xibo-player/schedule.xml "
                "/var/lib/xibo-player/cacheFile.xml 2>/dev/null || true; "
                "echo '--- cmsSettings ---'; "
                "cat /var/lib/xibo-player/cmsSettings.xml 2>/dev/null || true; "
                "echo '--- entrypoint/player log ---'; "
                "tail -n 80 /artifacts/player.log 2>/dev/null || true; "
                "docker_logs=$(sed -n '1,40p' /artifacts/xvfb.log 2>/dev/null || true); "
                "echo \"$docker_logs\""
            ),
        ],
        check=False,
    )
    out = probe.stdout or ""
    count = 0
    for line in out.splitlines():
        if line.startswith("library_files="):
            try:
                count = int(line.split("=", 1)[1].strip())
            except ValueError:
                count = 0
            break
    LOG.info("Player library file count=%s", count)
    if count < min_library_files:
        raise PipelineError(
            "Xibo player library appears empty after sync wait — "
            "framebuffer would not show published exhibit content.\n"
            f"diagnostics:\n{out[-3000:]}"
        )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(settings: Settings) -> int:
    from exhibit_layout import (  # local package alongside this script
        PipelineError as LayoutPipelineError,
        publish_exhibit_layout,
        timeline_path_for,
    )

    allow_fixture = settings.media_path.resolve() == DEFAULT_FIXTURE.resolve()
    ensure_media_ready(settings.media_path, allow_generate_fixture=allow_fixture)
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cms_url": settings.cms_url,
        "exhibit_slug": settings.exhibit_slug,
        "record_duration": settings.record_duration,
        "media_path": str(settings.media_path),
        "preview_only": settings.preview_only,
        "fast": settings.fast,
        "rebuild_player": settings.rebuild_player,
        "skip_html_packages": settings.skip_html_packages,
        "image_only_layout": settings.image_only_layout,
        "steps": [],
    }
    client = XiboClient(settings.cms_url)
    LOG.info(
        "QA target exhibit=%s media=%s record_duration=%ss preview_only=%s fast=%s "
        "skip_html=%s image_only=%s",
        settings.exhibit_slug,
        settings.media_path,
        settings.record_duration,
        settings.preview_only,
        settings.fast,
        settings.skip_html_packages,
        settings.image_only_layout,
    )

    try:
        if not settings.skip_up:
            stack_up(settings)
            report["steps"].append("compose_up")

        client.wait_until_ready()
        report["steps"].append("cms_ready")

        xmr_private = os.environ.get("XIBO_XMR_PRIVATE_ADDRESS", "http://cms-xmr:8081").strip()
        xmr_public = os.environ.get("XIBO_XMR_ADDRESS", "tcp://cms-xmr:9505").strip()
        configure_xmr_settings(private_address=xmr_private, public_address=xmr_public)
        report["xmr_private_address"] = xmr_private
        report["xmr_public_address"] = xmr_public
        report["steps"].append("xmr_configured")

        client_id = settings.client_id
        client_secret = settings.client_secret
        if not client_id or not client_secret:
            client_id, client_secret = client.bootstrap_application(
                settings.admin_user,
                settings.admin_password,
            )
            report["bootstrapped_client_id"] = client_id
            LOG.info(
                "Bootstrapped OAuth client_id=%s (secret redacted; export to config.env to reuse)",
                client_id,
            )

        token_error: Optional[Exception] = None
        for attempt in range(1, 7):
            try:
                client.obtain_token(client_id, client_secret)
                token_error = None
                break
            except Exception as exc:  # noqa: BLE001
                token_error = exc
                LOG.warning("Token attempt %s/6 failed: %s", attempt, exc)
                time.sleep(5)
        if token_error is not None:
            raise PipelineError(f"OAuth token exchange failed after retries: {token_error}")
        report["steps"].append("oauth_token")

        # Always prefer the live CMS SERVER_KEY. config.env / XIBO_CMS_KEY drifts
        # across `down -v` recreates while player-runtime bind mounts survive.
        live_key = client.get_cms_server_key()
        if settings.cms_key and settings.cms_key != live_key:
            LOG.warning(
                "Ignoring XIBO_CMS_KEY from env (len=%s); using live SERVER_KEY (len=%s)",
                len(settings.cms_key),
                len(live_key),
            )
        cms_key = live_key
        LOG.info("Using SERVER_KEY from CMS database (len=%s)", len(cms_key))

        hardware_key = os.environ.get("XIBO_HARDWARE_KEY", "qa-kiosk-01-hw")
        cms_internal = os.environ.get("XIBO_CMS_INTERNAL_URL", "http://cms-web")

        if settings.preview_only:
            timeline_meta = prepare_timeline_preview(settings)
            if timeline_meta:
                report["renderer"] = "timeline-preview"
                report["timeline_path"] = timeline_meta.get("timeline_path")
                report["steps"].append("timeline_preview_rendered")
            else:
                report["renderer"] = "static-fallback"
        else:
            report["renderer"] = "xibo-player"
            # Avoid stale Chromium preview HTML confusing operators.
            if TIMELINE_PREVIEW_DIR.is_dir():
                shutil.rmtree(TIMELINE_PREVIEW_DIR, ignore_errors=True)

        provision_player_cms_config(
            settings=settings,
            cms_url=cms_internal,
            cms_key=cms_key,
            display_name=settings.display_name,
            hardware_key=hardware_key,
            recreate=True,
        )
        time.sleep(2 if settings.fast else 5)

        try:
            client.register_display_via_xmds(
                server_key=cms_key,
                hardware_key=hardware_key,
                display_name=settings.display_name,
            )
        except PipelineError as exc:
            LOG.warning("XMDS register fallback failed (player may still self-register): %s", exc)

        # Authorise as soon as the display row exists so the player's next
        # RegisterDisplay is READY and Soap5 persists xmrChannel/xmrPubKey.
        try:
            early = client.wait_for_display(
                settings.display_name,
                timeout_seconds=60 if settings.fast else 120,
            )
            if int(early.get("licensed") or 0) != 1:
                client.authorise_display(early, hardware_key=hardware_key)
                LOG.info("Early-authorised display so XMR channel can be persisted")
        except PipelineError as exc:
            LOG.warning("Early display authorise skipped: %s", exc)

        final_layout_id: int
        campaign_id: int
        layout_duration = max(15, settings.record_duration)
        # keep-stack leaves prior layouts; unique names avoid 409 rename collisions.
        run_layout_name = f"{settings.layout_name}-{time.strftime('%H%M%S')}"
        LOG.info("Using layout name %s", run_layout_name)

        if settings.preview_only:
            # Chromium escape hatch: still publish a simple single-image layout for CMS smoke.
            media_id = client.upload_media(
                settings.media_path, name=f"{settings.exhibit_slug}-qa"
            )
            report["media_id"] = media_id
            report["steps"].append("media_uploaded")
            layout = client.create_layout(run_layout_name)
            published_layout_id = int(layout.get("layoutId") or layout.get("layoutid"))
            campaign_id = int(
                layout.get("campaignId") or layout.get("campaignid") or published_layout_id
            )
            draft = client.ensure_media_on_layout(
                published_layout_id,
                media_id,
                duration=max(15, settings.record_duration),
            )
            report["draft_layout_id"] = int(draft.get("layoutId") or draft.get("layoutid") or 0)
            parent_id = int(draft.get("parentId") or published_layout_id)
            published = client.publish_layout(parent_id)
            final_layout_id = parent_id
            campaign_id = int(
                published.get("campaignId") or published.get("campaignid") or campaign_id
            )
            report["layout_id"] = final_layout_id
            report["campaign_id"] = campaign_id
            report["steps"].append("layout_published")
        else:
            timeline = timeline_path_for(settings.exhibit_slug)
            if timeline.is_file():
                try:
                    published_meta = publish_exhibit_layout(
                        client,
                        exhibit_slug=settings.exhibit_slug,
                        layout_name=run_layout_name,
                        image_only=settings.image_only_layout,
                        skip_html_packages=settings.skip_html_packages,
                    )
                except LayoutPipelineError as exc:
                    raise PipelineError(str(exc)) from exc
                final_layout_id = int(published_meta["layout_id"])
                campaign_id = int(published_meta["campaign_id"])
                layout_duration = int(published_meta.get("layout_duration") or layout_duration)
                report["layout_id"] = final_layout_id
                report["campaign_id"] = campaign_id
                report["draft_layout_id"] = published_meta.get("draft_layout_id")
                report["media_ids"] = published_meta.get("media_ids")
                report["timeline_path"] = published_meta.get("timeline_path")
                report["regions"] = published_meta.get("regions")
                report["layout_duration"] = layout_duration
                report["steps"].append("exhibit_layout_published")
            else:
                LOG.info(
                    "No timeline.yaml for %s; falling back to single-image layout",
                    settings.exhibit_slug,
                )
                media_id = client.upload_media(
                    settings.media_path, name=f"{settings.exhibit_slug}-qa"
                )
                report["media_id"] = media_id
                report["steps"].append("media_uploaded")
                layout = client.create_layout(run_layout_name)
                published_layout_id = int(layout.get("layoutId") or layout.get("layoutid"))
                campaign_id = int(
                    layout.get("campaignId") or layout.get("campaignid") or published_layout_id
                )
                draft = client.ensure_media_on_layout(
                    published_layout_id,
                    media_id,
                    duration=max(15, settings.record_duration),
                )
                report["draft_layout_id"] = int(
                    draft.get("layoutId") or draft.get("layoutid") or 0
                )
                parent_id = int(draft.get("parentId") or published_layout_id)
                published = client.publish_layout(parent_id)
                final_layout_id = parent_id
                campaign_id = int(
                    published.get("campaignId") or published.get("campaignid") or campaign_id
                )
                report["layout_id"] = final_layout_id
                report["campaign_id"] = campaign_id
                report["steps"].append("layout_published")

        display = client.wait_for_display(settings.display_name, timeout_seconds=180)
        if int(display.get("licensed") or 0) != 1:
            client.authorise_display(display, hardware_key=hardware_key)
            display = client.find_display(settings.display_name) or display
        display_group_id = int(display["displayGroupId"])
        client.set_default_layout(display, final_layout_id, hardware_key=hardware_key)
        try:
            cleared = client.clear_schedule_for_display_group(display_group_id)
            report["schedule_cleared"] = cleared
            client.schedule_layout(display_group_id, campaign_id, event_name="qa-schedule")
        except PipelineError as exc:
            LOG.warning("Schedule create failed (continuing without schedule event): %s", exc)

        # CMS Soap5 only persists xmrChannel on READY RegisterDisplay. Authorise first,
        # then bounce the player so it re-registers while licensed and fills XMR fields.
        # Never call pipeline XMDS register after this point (it would wipe xmrChannel).
        if not settings.preview_only:
            provision_player_cms_config(
                settings=settings,
                cms_url=cms_internal,
                cms_key=cms_key,
                display_name=settings.display_name,
                hardware_key=hardware_key,
                recreate=not settings.fast,
            )
            if settings.fast:
                restart_player_container(fast=True)
            LOG.info(
                "Waiting for player READY RegisterDisplay to publish xmrChannel "
                "(Soap5 ignores XMR fields while WAITING)"
            )
            xmr_wait = 25 if settings.fast else 90
            display = wait_for_xmr_channel(
                client, settings.display_name, timeout_seconds=xmr_wait
            ) or display

        change_duration = max(120, settings.record_duration + 30, layout_duration + 30)
        collected, changed = push_layout_to_display(
            client,
            display_name=settings.display_name,
            display_group_id=display_group_id,
            layout_id=final_layout_id,
            change_duration=change_duration,
            fast=settings.fast,
            campaign_id=campaign_id,
        )
        report["xmr_collect"] = collected
        report["xmr_change_layout"] = changed
        report["steps"].append("xmr_collect_and_change_layout")

        if settings.preview_only:
            wait_s = 5
            LOG.info("Preview mode; waiting %ss for Chromium paint before capture", wait_s)
            time.sleep(wait_s)
        else:
            wait_for_player_library(
                min_library_files=1,
                timeout_seconds=max(settings.capture_wait_seconds, 35 if settings.fast else 90),
                poll_seconds=4 if settings.fast else 5,
            )
            # Post-XMR: require the player binary itself (not only Xvfb) before scrot.
            paint_stable = 4 if settings.fast else 8
            wait_for_player_process_alive(
                timeout_seconds=max(settings.capture_wait_seconds, 45 if settings.fast else 90),
                stable_seconds=paint_stable,
            )

        screenshot = capture_framebuffer(
            settings.artifact_dir,
            record_duration=settings.record_duration,
            also_video=settings.record_video,
            require_player_process=not settings.preview_only,
            paint_stable_seconds=4 if settings.fast else 6,
        )
        report["screenshot"] = str(screenshot)
        clip = settings.artifact_dir / screenshot.name.replace("frame-", "clip-").replace(
            ".png", ".mp4"
        )
        if clip.is_file():
            report["video"] = str(clip)
        report["steps"].append("captured")

        verification = verify_capture(screenshot)
        report["verification"] = verification
        report["steps"].append("verified")
        report["status"] = "passed"
        LOG.info("Visual verification passed: %s", verification)
        return 0

    except Exception as exc:
        LOG.exception("Pipeline failed: %s", exc)
        report["status"] = "failed"
        report["error"] = str(exc)
        return 1
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report_path = write_report(settings.artifact_dir, report)
        LOG.info("Wrote report %s", report_path)
        if not settings.keep_stack:
            try:
                stack_down(settings)
            except Exception as cleanup_exc:  # noqa: BLE001
                LOG.error("Cleanup failed: %s", cleanup_exc)
        else:
            LOG.info("Leaving stack running (--keep-stack)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exhibit",
        default=None,
        help=f"Exhibit slug under exhibits/ (default: {DEFAULT_EXHIBIT_SLUG} or QA_EXHIBIT_SLUG)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help=f"Seconds of framebuffer video to record (default: {DEFAULT_RECORD_DURATION} or QA_RECORD_DURATION)",
    )
    parser.add_argument(
        "--media",
        help="Override media path (skips exhibit manifest resolution)",
    )
    parser.add_argument("--artifact-dir", help="Host directory for captures and qa-report.json")
    parser.add_argument("--capture-wait", type=int, default=None, help="Seconds to wait before capture")
    parser.add_argument(
        "--fast",
        action="store_true",
        help=(
            "Faster iteration: skip player image rebuild, keep stack, short XMR waits, "
            "poll library instead of fixed sleep, PNG-only (implies --keep-stack)"
        ),
    )
    parser.add_argument(
        "--rebuild-player",
        action="store_true",
        help="Force docker compose --build for the player image (use after Dockerfile/entrypoint changes)",
    )
    parser.add_argument(
        "--record-video",
        action="store_true",
        help="Record MP4 even in --fast mode",
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Skip MP4 capture (PNG only)",
    )
    parser.add_argument("--keep-stack", action="store_true", help="Do not docker compose down -v on exit")
    parser.add_argument("--skip-up", action="store_true", help="Assume compose stack is already running")
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Debug: Chromium timeline preview capture instead of Xibo Linux Player",
    )
    parser.add_argument(
        "--image-only-layout",
        action="store_true",
        help="Bisect: publish a single-region image-only layout (QA_IMAGE_ONLY_LAYOUT=1)",
    )
    parser.add_argument(
        "--skip-html-packages",
        action="store_true",
        help="Skip html-package widgets when publishing (default in headless player mode)",
    )
    parser.add_argument(
        "--include-html-packages",
        action="store_true",
        help="Include html-package widgets (overrides default QA_SKIP_HTML_PACKAGES)",
    )
    parser.add_argument("--verify-only", metavar="PNG", help="Only run Pillow verification on an existing PNG")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.verify_only:
        result = verify_capture(Path(args.verify_only))
        print(json.dumps(result, indent=2))
        return 0

    if not shutil.which("docker"):
        LOG.error("docker is required on PATH")
        return 2
    if not COMPOSE_FILE.is_file():
        LOG.error("Missing compose file: %s", COMPOSE_FILE)
        return 2

    # Ensure ops/qa is importable for exhibit_layout.
    if str(QA_DIR) not in sys.path:
        sys.path.insert(0, str(QA_DIR))

    settings = Settings.from_env(args)
    return run_pipeline(settings)


if __name__ == "__main__":
    sys.exit(main())
