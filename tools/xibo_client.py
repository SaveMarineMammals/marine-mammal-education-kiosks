"""Production Xibo CMS REST client (media + layouts only).

Intentionally omits schedule, display, and XMR action APIs so content sync
cannot mutate facility schedules.
"""

from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse, urlunparse

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

LOG = logging.getLogger("mmek.xibo")

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_DEFAULT_TLS_HOST = "server.kiosks.local.belize.savemarinemammals.com"
_MAX_REDIRECTS = 5


def _is_loopback_http(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "http" and (parsed.hostname or "") in _LOOPBACK_HOSTS


def _tls_hostname(*, allow_default: bool = False) -> str:
    for key in ("XIBO_CMS_TLS_HOST", "CMS_HOSTNAME", "CMS_SERVER_NAME"):
        value = (os.environ.get(key) or "").strip()
        if value:
            return value
    if allow_default:
        return _DEFAULT_TLS_HOST
    return ""


def resolve_cms_base_url(base_url: str) -> str:
    """Pick an API base URL that survives Xibo Force HTTPS behind Caddy.

    Loopback ``http://127.0.0.1:8080`` is still the preferred operator setting,
    but Force HTTPS redirects OAuth to ``https://127.0.0.1/`` where Caddy has no
    certificate. When the env URL is loopback HTTP, use the public CMS hostname
    over HTTPS instead (same host Caddy serves on :443).
    """
    trimmed = base_url.rstrip("/")
    if not _is_loopback_http(trimmed):
        return trimmed
    tls_host = _tls_hostname(allow_default=False)
    if tls_host:
        resolved = f"https://{tls_host}"
        if resolved != trimmed:
            LOG.info(
                "XIBO_CMS_URL is loopback HTTP; using %s for API (Force HTTPS / Caddy)",
                resolved,
            )
        return resolved
    return trimmed


def _rewrite_loopback_https(location: str) -> str:
    """Rewrite https://127.0.0.1 redirects to the CMS TLS hostname."""
    if not location:
        return location
    parsed = urlparse(location)
    if parsed.scheme != "https" or (parsed.hostname or "") not in _LOOPBACK_HOSTS:
        return location
    tls_host = _tls_hostname(allow_default=True)
    if not tls_host:
        return location
    port = parsed.port
    netloc = f"{tls_host}:{port}" if port and port != 443 else tls_host
    return urlunparse(parsed._replace(netloc=netloc))


class XiboError(RuntimeError):
    """Fatal CMS API error."""


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _plain_text_widget_html(text: str, *, region: Optional[str] = None) -> str:
    """HTML body for a non-ticker text widget (region selects hero vs insight band)."""
    region_key = (region or "").strip()
    if region_key == "hero-labels":
        return (
            "<div style=\"font-family:'Source Sans 3',Segoe UI,sans-serif;"
            "font-size:40px;line-height:1.3;font-weight:600;color:#F4F8FC;"
            "background:rgba(8,24,40,0.62);padding:20px 24px;box-sizing:border-box;"
            "width:100%;height:100%;white-space:pre-wrap;\">"
            f"{_escape_html(text)}</div>"
        )
    band_bg = "#0A2A3A"
    return (
        "<div style=\"font-family:'Source Sans 3',Segoe UI,sans-serif;"
        "font-size:36px;line-height:1.35;font-weight:600;color:#F4F8FC;"
        f"background:{band_bg};padding:24px 28px;box-sizing:border-box;"
        "width:100%;height:100%;white-space:pre-wrap;\">"
        f"{_escape_html(text)}</div>"
    )


def _mime_for_path(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed
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


def client_from_env(*, timeout: int = 120) -> "XiboClient":
    """Build an authenticated client from ``XIBO_*`` environment variables."""
    if requests is None:
        raise XiboError("requests is required: pip install requests")
    base_url = (os.environ.get("XIBO_CMS_URL") or "").strip()
    client_id = (os.environ.get("XIBO_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("XIBO_CLIENT_SECRET") or "").strip()
    if not base_url or not client_id or not client_secret:
        raise XiboError(
            "Set XIBO_CMS_URL, XIBO_CLIENT_ID, and XIBO_CLIENT_SECRET "
            "(see ops/cms/cms-sync.env.example)"
        )
    client = XiboClient(resolve_cms_base_url(base_url), timeout=timeout)
    client.obtain_token(client_id, client_secret)
    return client


class XiboClient:
    """OAuth2 client_credentials client for Library + Layout APIs."""

    def __init__(self, base_url: str, timeout: int = 120) -> None:
        if requests is None:
            raise XiboError("requests is required: pip install requests")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "mmek-cms-sync/1.0"}
        )
        self.timeout = timeout
        self.access_token: Optional[str] = None

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        kwargs.setdefault("timeout", self.timeout)
        allow_redirects = kwargs.pop("allow_redirects", True)
        url = self._url(path)
        response = self.session.request(
            method, url, allow_redirects=False, **kwargs
        )
        redirects = 0
        while (
            allow_redirects
            and response.status_code in (301, 302, 303, 307, 308)
            and redirects < _MAX_REDIRECTS
        ):
            location = response.headers.get("Location") or ""
            if response.status_code in (303,) and method.upper() != "GET":
                method = "GET"
            if not location.startswith(("http://", "https://")):
                location = urljoin(url, location)
            location = _rewrite_loopback_https(location)
            redirects += 1
            url = location
            response = self.session.request(
                method, url, allow_redirects=False, **kwargs
            )
        if response.status_code >= 400:
            body = response.text[:2000]
            raise XiboError(f"{method} {path} -> HTTP {response.status_code}: {body}")
        if not response.content:
            return None
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type or response.text[:1] in "{[":
            return response.json()
        return response.text

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
        if not isinstance(payload, dict):
            raise XiboError(f"Token response unexpected: {payload}")
        token = payload.get("access_token")
        if not token:
            raise XiboError(f"Token response missing access_token: {payload}")
        self.access_token = str(token)
        self.session.headers["Authorization"] = f"Bearer {token}"
        return self.access_token

    def ping(self) -> None:
        """Lightweight authenticated probe (layout list)."""
        self.request("GET", "/api/layout", params={"length": 1})

    # ------------------------------------------------------------------ media

    def find_media_by_name(self, name: str) -> Optional[dict[str, Any]]:
        try:
            payload = self.request(
                "GET", "/api/library", params={"media": name, "exactName": 1}
            )
        except XiboError as exc:
            LOG.debug("library lookup failed for %s: %s", name, exc)
            return None
        items = (
            payload
            if isinstance(payload, list)
            else payload.get("data")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(items, list):
            return None
        for item in items:
            if not isinstance(item, dict):
                continue
            item_name = str(item.get("name") or item.get("media") or "")
            if item_name.lower() == name.lower() or item_name.lower() == Path(name).stem.lower():
                return item
        if items and isinstance(items[0], dict):
            return items[0]
        return None

    def find_media_id_by_name(self, name: str) -> Optional[int]:
        item = self.find_media_by_name(name)
        if item is None:
            return None
        return _extract_id(item, keys=("mediaId", "id"))

    def media_has_tag(self, media: dict[str, Any], tag: str) -> bool:
        want = tag.lower()
        tags = media.get("tags") or media.get("tag") or []
        if isinstance(tags, str):
            return want in {t.strip().lower() for t in tags.split(",")}
        if isinstance(tags, list):
            for entry in tags:
                if isinstance(entry, str) and entry.lower() == want:
                    return True
                if isinstance(entry, dict):
                    name = str(entry.get("tag") or entry.get("name") or "").lower()
                    if name == want:
                        return True
        return False

    def upload_media(self, file_path: Path, name: Optional[str] = None) -> int:
        LOG.info("Uploading media %s", file_path)
        if not file_path.is_file():
            raise XiboError(f"Media file not found: {file_path}")

        display_name = name or file_path.stem
        mime = _mime_for_path(file_path)
        if file_path.suffix.lower() == ".zip":
            upload_name = f"{display_name}.htz"
            mime = "application/zip"
        else:
            upload_name = f"{display_name}{file_path.suffix.lower()}"

        with file_path.open("rb") as handle:
            files = {"files": (upload_name, handle, mime)}
            data = {"name": display_name}
            payload = self.request("POST", "/api/library", files=files, data=data)

        if isinstance(payload, dict):
            for item in payload.get("files") or []:
                if isinstance(item, dict) and item.get("error"):
                    err = str(item.get("error") or "")
                    if "already own media" in err.lower():
                        existing = self.find_media_id_by_name(display_name)
                        if existing is None:
                            existing = self.find_media_id_by_name(Path(upload_name).stem)
                        if existing is not None:
                            LOG.info(
                                "Reusing existing mediaId=%s for %s",
                                existing,
                                display_name,
                            )
                            return existing
                    raise XiboError(
                        f"Library rejected {upload_name}: {err} "
                        f"(type={item.get('type')}, size={item.get('size')})"
                    )

        media_id = _extract_id(payload, keys=("mediaId", "id"))
        if media_id is None:
            raise XiboError(f"Could not parse mediaId from upload response: {payload}")
        LOG.info("Uploaded mediaId=%s name=%s", media_id, display_name)
        return media_id

    def get_media(self, media_id: int) -> dict[str, Any]:
        """Return one Library record by id."""
        payload = self.request(
            "GET",
            "/api/library",
            params={"mediaId": int(media_id)},
        )
        items = (
            payload
            if isinstance(payload, list)
            else payload.get("data")
            if isinstance(payload, dict)
            else None
        )
        want = int(media_id)
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                found = item.get("mediaId", item.get("id"))
                if found is not None and int(found) == want:
                    return item
        raise XiboError(f"Media {media_id} not found")

    def edit_media(
        self,
        media_id: int,
        *,
        name: Optional[str] = None,
        tags: Optional[list[str]] = None,
        folder_id: Optional[int] = None,
        duration: Optional[int] = None,
    ) -> Any:
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
            data["media"] = name
        if tags is not None:
            # Xibo accepts comma-separated tags on edit.
            data["tags"] = ",".join(tags)
        if folder_id is not None:
            data["folderId"] = int(folder_id)
        if duration is not None:
            data["duration"] = int(duration)
        if not data:
            return None
        # PUT /api/library/{id} requires name, duration, and retired. A missing
        # duration is stored as NULL and Xibo answers HTTP 500.
        self._fill_library_edit_fields(media_id, data)
        LOG.info(
            "Editing mediaId=%s tags=%s folderId=%s duration=%s",
            media_id,
            tags,
            folder_id,
            data.get("duration"),
        )
        try:
            return self.request("PUT", f"/api/library/{media_id}", data=data)
        except XiboError as exc:
            # Older CMS builds may reject folderId; retry tags/name only.
            if folder_id is not None and "folder" in str(exc).lower():
                data.pop("folderId", None)
                if data:
                    return self.request("PUT", f"/api/library/{media_id}", data=data)
            raise

    def _fill_library_edit_fields(self, media_id: int, data: dict[str, Any]) -> None:
        """Preserve duration, retired, and enableStat across a library edit."""
        current: dict[str, Any] = {}
        try:
            current = self.get_media(media_id)
        except XiboError as exc:
            LOG.warning(
                "Could not read mediaId=%s before edit (%s); sending duration=10",
                media_id,
                exc,
            )
        if "name" not in data and current.get("name"):
            data["name"] = current["name"]
        if "duration" not in data:
            raw_duration = current.get("duration")
            data["duration"] = (
                int(raw_duration) if raw_duration not in (None, "") else 10
            )
        if "retired" not in data:
            data["retired"] = 1 if int(current.get("retired") or 0) else 0
        if "enableStat" not in data and current.get("enableStat") not in (None, ""):
            data["enableStat"] = current["enableStat"]

    def list_folders(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "/api/folder")
        if isinstance(payload, list):
            return [f for f in payload if isinstance(f, dict)]
        if isinstance(payload, dict):
            folders = payload.get("folders") or payload.get("data") or []
            if isinstance(folders, list):
                return [f for f in folders if isinstance(f, dict)]
            # Some builds return a nested tree under "children".
            roots = payload.get("children")
            if isinstance(roots, list):
                return self._flatten_folder_tree(roots)
        return []

    def _flatten_folder_tree(self, nodes: list[Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            out.append(node)
            children = node.get("children") or []
            if isinstance(children, list) and children:
                out.extend(self._flatten_folder_tree(children))
        return out

    def ensure_folder_path(self, parts: list[str]) -> Optional[int]:
        """Ensure nested Library folders exist; return leaf folderId (or None)."""
        clean = [p.strip() for p in parts if p and str(p).strip()]
        if not clean:
            return None
        try:
            folders = self.list_folders()
        except XiboError as exc:
            LOG.warning("Folder API unavailable (%s); skipping folder placement", exc)
            return None

        by_parent: dict[Optional[int], dict[str, dict[str, Any]]] = {}
        for folder in folders:
            fid = _extract_id(folder, keys=("folderId", "id"))
            parent = folder.get("parentId")
            parent_id = int(parent) if parent not in (None, "", 0, "0") else None
            name = str(folder.get("text") or folder.get("name") or folder.get("folder") or "")
            if not name or fid is None:
                continue
            by_parent.setdefault(parent_id, {})[name.lower()] = folder

        parent_id: Optional[int] = None
        # Root parent is often 1 on Xibo; treat missing as None and let create use default.
        for name in clean:
            siblings = by_parent.get(parent_id) or {}
            # Also try parent_id=1 as CMS root.
            if name.lower() not in siblings and parent_id is None:
                siblings = by_parent.get(1) or siblings
            existing = siblings.get(name.lower())
            if existing:
                parent_id = _extract_id(existing, keys=("folderId", "id"))
                continue
            LOG.info("Creating Library folder %r under parentId=%s", name, parent_id)
            data: dict[str, Any] = {"text": name}
            if parent_id is not None:
                data["parentId"] = parent_id
            try:
                created = self.request("POST", "/api/folder", data=data)
            except XiboError as exc:
                LOG.warning("Could not create folder %r: %s", name, exc)
                return parent_id
            new_id = _extract_id(created, keys=("folderId", "id"))
            if new_id is None and isinstance(created, dict):
                # Some responses nest under data.
                new_id = _extract_id(created.get("data"), keys=("folderId", "id"))
            if new_id is None:
                LOG.warning("Folder create returned no id for %r: %s", name, created)
                return parent_id
            parent_id = new_id
            by_parent.setdefault(
                int(data["parentId"]) if "parentId" in data else None, {}
            )[name.lower()] = {"folderId": new_id, "text": name}
        return parent_id

    # ---------------------------------------------------------------- layouts

    def find_layout_by_name(self, name: str) -> Optional[dict[str, Any]]:
        payload = self.request("GET", "/api/layout", params={"layout": name, "exactName": 1})
        items = payload if isinstance(payload, list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_name = str(item.get("layout") or item.get("name") or "")
            if item_name.lower() == name.lower():
                # Prefer published parent rows.
                status = str(item.get("publishedStatus") or "").lower()
                if status == "draft" or item.get("publishedStatusId") == 2:
                    continue
                return item
        for item in items:
            if isinstance(item, dict):
                item_name = str(item.get("layout") or item.get("name") or "")
                if item_name.lower() == name.lower():
                    return item
        return None

    def create_layout(self, name: str, width: int = 1920, height: int = 1080) -> dict[str, Any]:
        LOG.info("Creating layout %s", name)
        payload = self.request(
            "POST",
            "/api/layout",
            data={"name": name, "resolutionId": self._resolution_id_for(width, height)},
        )
        layout = payload[0] if isinstance(payload, list) else payload
        if not isinstance(layout, dict):
            raise XiboError(f"Unexpected create layout response: {payload}")
        return layout

    def ensure_layout(self, name: str, width: int = 1920, height: int = 1080) -> dict[str, Any]:
        existing = self.find_layout_by_name(name)
        if existing is not None:
            LOG.info(
                "Reusing layout %s layoutId=%s",
                name,
                existing.get("layoutId") or existing.get("layoutid"),
            )
            return existing
        return self.create_layout(name, width=width, height=height)

    def checkout_layout(self, layout_id: int) -> dict[str, Any]:
        LOG.info("Checking out layoutId=%s", layout_id)
        payload = self.request("PUT", f"/api/layout/checkout/{layout_id}")
        result = payload[0] if isinstance(payload, list) else payload
        if not isinstance(result, dict):
            raise XiboError(f"Unexpected checkout response: {payload}")
        return result

    def publish_layout(self, layout_id: int) -> dict[str, Any]:
        LOG.info("Publishing layoutId=%s", layout_id)
        payload = self.request(
            "PUT", f"/api/layout/publish/{layout_id}", data={"publishNow": 1}
        )
        result = payload[0] if isinstance(payload, list) else payload
        if not isinstance(result, dict):
            return result if isinstance(result, dict) else {}
        return result

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
        draft = self.get_layout(parent_id=published_layout_id)
        if draft:
            return draft

        current = self.get_layout(layout_id=published_layout_id)
        if current and (
            str(current.get("publishedStatus") or "").lower() == "draft"
            or current.get("publishedStatusId") == 2
        ):
            return current

        try:
            return self.checkout_layout(published_layout_id)
        except XiboError as exc:
            draft = self.get_layout(parent_id=published_layout_id)
            if draft:
                return draft
            raise XiboError(
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
        result = payload[0] if isinstance(payload, list) else payload
        if not isinstance(result, dict):
            raise XiboError(f"Unexpected add region response: {payload}")
        return result

    def delete_region(self, region_id: int) -> None:
        self.request("DELETE", f"/api/region/{region_id}")

    def edit_region(
        self,
        region_id: int,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        top: Optional[int] = None,
        left: Optional[int] = None,
        z_index: Optional[int] = None,
        background_color: Optional[str] = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if width is not None:
            data["width"] = int(width)
        if height is not None:
            data["height"] = int(height)
        if top is not None:
            data["top"] = int(top)
        if left is not None:
            data["left"] = int(left)
        if z_index is not None:
            data["zIndex"] = int(z_index)
        if background_color is not None:
            data["backgroundColor"] = background_color
        if not data:
            return {}
        payload = self.request("PUT", f"/api/region/{region_id}", data=data)
        result = payload[0] if isinstance(payload, list) else (payload or {})
        return result if isinstance(result, dict) else {}

    def edit_layout(
        self,
        layout_id: int,
        *,
        name: Optional[str] = None,
        duration: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if duration is not None:
            data["duration"] = int(duration)
        if tags is not None:
            data["tags"] = ",".join(tags)
        if not data:
            return {}
        payload = self.request("PUT", f"/api/layout/{layout_id}", data=data)
        result = payload[0] if isinstance(payload, list) else (payload or {})
        return result if isinstance(result, dict) else {}

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
                except XiboError as exc:
                    LOG.warning("Failed to delete regionId=%s: %s", rid, exc)

    def assign_media_to_playlist(
        self,
        playlist_id: int,
        media_id: int,
        *,
        duration: int,
    ) -> Any:
        return self.request(
            "POST",
            f"/api/playlist/library/assign/{playlist_id}",
            data=[("media[]", str(media_id)), ("duration", str(int(duration)))],
        )

    def add_widget(self, widget_type: str, playlist_id: int) -> dict[str, Any]:
        payload = self.request("POST", f"/api/playlist/widget/{widget_type}/{playlist_id}")
        widget = payload[0] if isinstance(payload, list) else payload
        if not isinstance(widget, dict):
            raise XiboError(f"Unexpected widget add response: {payload}")
        return widget

    def edit_widget(self, widget_id: int, data: dict[str, Any] | list[tuple[str, str]]) -> Any:
        return self.request("PUT", f"/api/playlist/widget/{widget_id}", data=data)

    def add_spacer_widget(self, playlist_id: int, duration: int) -> int:
        duration = max(1, int(duration))
        widget = self.add_widget("spacer", playlist_id)
        widget_id = int(widget.get("widgetId") or widget.get("widgetid") or 0)
        if not widget_id:
            raise XiboError(f"spacer widget missing id: {widget}")
        self.edit_widget(widget_id, {"duration": duration, "useDuration": 1})
        return widget_id

    def add_text_widget(
        self,
        playlist_id: int,
        text: str,
        duration: int,
        *,
        effect: str = "none",
        region: Optional[str] = None,
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
            except XiboError as exc:
                last_error = exc
                LOG.debug("text widget add via %s failed: %s", path, exc)
        if widget is None:
            raise XiboError(f"Unable to add text widget: {last_error}")

        widget_id = int(widget.get("widgetId") or widget.get("widgetid") or 0)
        if not widget_id:
            raise XiboError(f"text widget missing id: {widget}")

        effect_key = (effect or "none").strip()
        plain = " ".join(text.split())
        if effect_key == "tickerScroll":
            # Region background paints the band; marquee HTML must stay text-only
            # (a width:100% colored box scrolls as a panel and dies mid-pass).
            crawl = f"{plain}        ·        " * 4
            html = (
                "<span style=\"font-family:'Source Sans 3',Segoe UI,sans-serif;"
                "font-size:34px;line-height:140px;font-weight:600;color:#E8F4F8;"
                "white-space:nowrap;padding:0 32px;\">"
                f"{_escape_html(crawl.strip())}</span>"
            )
            edit_payload: dict[str, Any] = {
                "duration": duration,
                "useDuration": 1,
                "text": html,
                "ta_text": html,
                "effect": "marqueeLeft",
                "speed": 2,
            }
        else:
            html = _plain_text_widget_html(text, region=region)
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
        except XiboError as exc:
            LOG.warning("text widget edit with HTML/effect failed (%s); retrying plain", exc)
            fallback: dict[str, Any] = {
                "duration": duration,
                "useDuration": 1,
                "text": plain if effect_key == "tickerScroll" else text,
            }
            if effect_key == "tickerScroll":
                fallback["effect"] = "marqueeLeft"
                fallback["speed"] = 2
            self.edit_widget(widget_id, fallback)
        return widget_id

    def _resolution_id_for(self, width: int, height: int) -> int:
        try:
            resolutions = self.request(
                "GET", "/api/resolution", params={"width": width, "height": height}
            )
            if isinstance(resolutions, list) and resolutions:
                return int(resolutions[0]["resolutionId"])
        except XiboError:
            pass
        try:
            created = self.request(
                "POST",
                "/api/resolution",
                data={
                    "resolution": f"MMEK {width}x{height}",
                    "width": width,
                    "height": height,
                },
            )
            rid = _extract_id(created, keys=("resolutionId", "id"))
            if rid is not None:
                return rid
        except XiboError:
            pass
        return 1
