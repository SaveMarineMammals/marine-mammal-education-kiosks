"""Build and upsert stable Xibo layouts from exhibit timeline.yaml.

Production layouts use the stable name ``mmek-<slug>`` so facility schedules
that bind the layout campaign keep working across content refreshes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Protocol

from pathutil import resolve_manifest_path
from xibo_client import XiboError

LOG = logging.getLogger("mmek.xibo_layout")

ROOT = Path(__file__).resolve().parents[1]
EXHIBITS_DIR = ROOT / "exhibits"

LAYERED_STILLS_REGIONS: dict[str, dict[str, int]] = {
    "background": {"left": 0, "top": 0, "width": 1920, "height": 1080, "zIndex": 0},
    "midground": {"left": 0, "top": 0, "width": 1920, "height": 1080, "zIndex": 1},
    "text": {"left": 160, "top": 720, "width": 1600, "height": 280, "zIndex": 2},
    "accent": {"left": 1580, "top": 40, "width": 280, "height": 280, "zIndex": 3},
}

GLANCE_AND_MATCH_REGIONS: dict[str, dict[str, int]] = {
    "insights-bg": {"left": 800, "top": 0, "width": 1120, "height": 1080, "zIndex": 0},
    "hero-bg": {"left": 0, "top": 0, "width": 800, "height": 1080, "zIndex": 1},
    "hero-still": {"left": 40, "top": 300, "width": 720, "height": 740, "zIndex": 2},
    "hero-labels": {"left": 24, "top": 24, "width": 752, "height": 260, "zIndex": 3},
    "insights-art": {"left": 840, "top": 32, "width": 1040, "height": 440, "zIndex": 2},
    "insights-copy": {"left": 840, "top": 500, "width": 1040, "height": 280, "zIndex": 3},
    "ticker": {"left": 800, "top": 940, "width": 1120, "height": 140, "zIndex": 4},
}


def stable_layout_name(slug: str) -> str:
    return f"mmek-{slug}"


def region_geometry_for_timeline(timeline: dict[str, Any]) -> dict[str, dict[str, int]]:
    template = str(timeline.get("template") or "").strip()
    regions = timeline.get("regions") or {}
    region_names = set(regions.keys()) if isinstance(regions, dict) else set()
    glance_keys = {
        "hero",
        "hero-bg",
        "hero-still",
        "hero-labels",
        "insights",
        "insights-bg",
        "insights-art",
        "insights-copy",
        "ticker",
    }
    if template == "glance-and-match" or region_names & glance_keys:
        if "hero-bg" in region_names or "hero-still" in region_names:
            return GLANCE_AND_MATCH_REGIONS
        if "insights-art" in region_names or "insights-copy" in region_names:
            return {
                "insights-bg": GLANCE_AND_MATCH_REGIONS["insights-bg"],
                "hero": {"left": 0, "top": 0, "width": 800, "height": 1080, "zIndex": 1},
                "insights-art": GLANCE_AND_MATCH_REGIONS["insights-art"],
                "insights-copy": GLANCE_AND_MATCH_REGIONS["insights-copy"],
                "ticker": GLANCE_AND_MATCH_REGIONS["ticker"],
            }
        legacy = {
            "hero": {"left": 0, "top": 0, "width": 800, "height": 1080, "zIndex": 1},
            "insights": {
                "left": 800,
                "top": 0,
                "width": 1120,
                "height": 900,
                "zIndex": 1,
            },
            "ticker": GLANCE_AND_MATCH_REGIONS["ticker"],
        }
        if "insights-bg" in region_names:
            legacy = {"insights-bg": GLANCE_AND_MATCH_REGIONS["insights-bg"], **legacy}
        return legacy
    return LAYERED_STILLS_REGIONS


class XiboLayoutClient(Protocol):
    def upload_media(self, file_path: Path, name: Optional[str] = None) -> int: ...

    def ensure_layout(self, name: str, width: int = 1920, height: int = 1080) -> dict[str, Any]: ...

    def resolve_draft_layout(self, published_layout_id: int) -> dict[str, Any]: ...

    def get_layout(
        self,
        *,
        layout_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> Optional[dict[str, Any]]: ...

    def clear_regions(self, draft_layout_id: int) -> None: ...

    def edit_layout(
        self,
        layout_id: int,
        *,
        name: Optional[str] = None,
        duration: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]: ...

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
    ) -> dict[str, Any]: ...

    def _playlist_id_from_region(self, region: dict[str, Any]) -> Optional[int]: ...

    def assign_media_to_playlist(
        self,
        playlist_id: int,
        media_id: int,
        *,
        duration: int,
    ) -> Any: ...

    def add_spacer_widget(self, playlist_id: int, duration: int) -> int: ...

    def add_text_widget(
        self,
        playlist_id: int,
        text: str,
        duration: int,
        *,
        effect: str = "none",
    ) -> int: ...

    def publish_layout(self, layout_id: int) -> dict[str, Any]: ...


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise XiboError("PyYAML is required: pip install pyyaml") from exc
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise XiboError(f"YAML root must be a mapping: {path}")
    return data


def timeline_path_for(slug: str) -> Path:
    return EXHIBITS_DIR / slug / "layouts" / "timeline.yaml"


def _local_paths_for_asset(exhibit_dir: Path, asset: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    uri = str(asset.get("uri") or "").strip()
    if uri and not uri.startswith("sha256/") and "://" not in uri:
        candidates.append(resolve_manifest_path(uri, root=ROOT))
    filename = str(asset.get("filename") or "").strip()
    if filename:
        candidates.append(exhibit_dir / "media" / "assets" / filename)
    preview = str(asset.get("preview") or "").strip()
    if preview:
        candidates.append(exhibit_dir / "media" / "previews" / preview)
    return candidates


def resolve_asset_upload_path(
    exhibit_dir: Path,
    asset: dict[str, Any],
    *,
    widget_type: str,
) -> Path:
    filename = str(asset.get("filename") or "").strip()
    uri = str(asset.get("uri") or "").strip()
    candidates: list[Path] = []

    if widget_type == "html-package":
        for ext in (".zip", ".htz"):
            if filename:
                stem = Path(filename).stem
                candidates.append(exhibit_dir / "media" / "assets" / f"{stem}{ext}")
        if uri and not uri.startswith("sha256/") and "://" not in uri:
            resolved = resolve_manifest_path(uri, root=ROOT)
            candidates.append(resolved)
            if resolved.suffix.lower() in {".zip", ".htz", ".html"}:
                candidates.append(resolved.with_suffix(".zip"))
                candidates.append(resolved.with_suffix(".htz"))
        asset_id = str(asset.get("id") or "").strip()
        if asset_id:
            candidates.append(exhibit_dir / "media" / "assets" / f"{asset_id}.zip")
            candidates.append(exhibit_dir / "media" / "assets" / f"{asset_id}.htz")
    else:
        candidates.extend(_local_paths_for_asset(exhibit_dir, asset))

    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            return path

    raise XiboError(
        f"No local upload file for asset id={asset.get('id')!r} type={widget_type} "
        f"(looked under {exhibit_dir / 'media' / 'assets'})"
    )


def collect_timeline_widgets(timeline: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    regions = timeline.get("regions") or {}
    out: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(regions, dict):
        return out
    for region_name, region in regions.items():
        if not isinstance(region, dict):
            continue
        for widget in region.get("widgets") or []:
            if isinstance(widget, dict):
                out.append((str(region_name), widget))
    return out


def _widget_window(widget: dict[str, Any]) -> tuple[float, float]:
    start = float(widget.get("startSeconds") or 0)
    duration = float(widget.get("durationSeconds") or 0)
    return start, start + max(duration, 0)


def assign_overlap_tracks(widgets: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    ordered = sorted(widgets, key=lambda w: float(w.get("startSeconds") or 0))
    tracks: list[list[dict[str, Any]]] = []
    track_ends: list[float] = []
    for widget in ordered:
        start, end = _widget_window(widget)
        placed = False
        for idx, track_end in enumerate(track_ends):
            if start >= track_end - 1e-6:
                tracks[idx].append(widget)
                track_ends[idx] = end
                placed = True
                break
        if not placed:
            tracks.append([widget])
            track_ends.append(end)
    return tracks


def fill_playlist_from_widgets(
    client: XiboLayoutClient,
    playlist_id: int,
    widgets: list[dict[str, Any]],
    *,
    media_ids: dict[str, int],
    layout_duration: int,
) -> None:
    cursor = 0.0
    for widget in sorted(widgets, key=lambda w: float(w.get("startSeconds") or 0)):
        start = float(widget.get("startSeconds") or 0)
        duration = max(1, int(round(float(widget.get("durationSeconds") or 1))))
        gap = int(round(start - cursor))
        if gap >= 1:
            client.add_spacer_widget(playlist_id, gap)
            cursor += gap

        wtype = str(widget.get("type") or "").strip()
        if wtype == "text":
            copy = str(widget.get("copy") or "").strip()
            effect = str(widget.get("effect") or "none").strip() or "none"
            client.add_text_widget(playlist_id, copy, duration, effect=effect)
        elif wtype in {"image", "html-package", ""}:
            asset_id = str(widget.get("asset") or "").strip()
            media_id = media_ids.get(asset_id)
            if media_id is None:
                raise XiboError(f"No uploaded media for asset {asset_id!r}")
            client.assign_media_to_playlist(playlist_id, media_id, duration=duration)
        else:
            raise XiboError(f"Unsupported timeline widget type: {wtype!r}")
        cursor = max(cursor, start) + duration

    trailing = int(round(layout_duration - cursor))
    if trailing >= 1:
        client.add_spacer_widget(playlist_id, trailing)


def upload_timeline_assets(
    client: XiboLayoutClient,
    *,
    slug: str,
    timeline: dict[str, Any],
    media_ids: Optional[dict[str, int]] = None,
) -> dict[str, int]:
    """Upload timeline assets; reuse ``media_ids`` map when provided by media sync."""
    exhibit_dir = EXHIBITS_DIR / slug
    manifest = load_yaml(exhibit_dir / "media" / "manifest.yaml")
    assets_by_id: dict[str, dict[str, Any]] = {}
    for asset in manifest.get("assets") or []:
        if isinstance(asset, dict) and asset.get("id"):
            assets_by_id[str(asset["id"])] = asset

    resolved: dict[str, int] = dict(media_ids or {})
    for _region, widget in collect_timeline_widgets(timeline):
        wtype = str(widget.get("type") or "").strip()
        if wtype == "text":
            continue
        asset_id = str(widget.get("asset") or "").strip()
        if not asset_id or asset_id in resolved:
            continue
        asset = assets_by_id.get(asset_id)
        if asset is None:
            raise XiboError(f"timeline references unknown asset id={asset_id!r}")
        path = resolve_asset_upload_path(exhibit_dir, asset, widget_type=wtype or "image")
        resolved[asset_id] = client.upload_media(path, name=f"{slug}-{asset_id}")
    LOG.info("Resolved %s timeline assets for exhibit=%s", len(resolved), slug)
    return resolved


def upsert_exhibit_layout(
    client: Optional[XiboLayoutClient],
    *,
    exhibit_slug: str,
    layout_name: Optional[str] = None,
    media_ids: Optional[dict[str, int]] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Update-in-place (or create once) the stable layout for an exhibit."""
    path = timeline_path_for(exhibit_slug)
    if not path.is_file():
        raise XiboError(f"Missing timeline for exhibit publish: {path}")

    timeline = load_yaml(path)
    name = layout_name or stable_layout_name(exhibit_slug)
    layout_duration = int(timeline.get("durationSeconds") or 90)
    tags = [f"exhibit:{exhibit_slug}", "mmek:managed"]

    if dry_run:
        widgets = collect_timeline_widgets(timeline)
        LOG.info(
            "Dry run: would upsert layout %s duration=%ss widgets=%s",
            name,
            layout_duration,
            len(widgets),
        )
        return {
            "layout_name": name,
            "layout_duration": layout_duration,
            "dry_run": True,
            "widget_count": len(widgets),
        }

    if client is None:
        raise XiboError("CMS client is required unless dry_run=True")

    resolved_media = upload_timeline_assets(
        client, slug=exhibit_slug, timeline=timeline, media_ids=media_ids
    )

    layout = client.ensure_layout(name)
    published_layout_id = int(layout.get("layoutId") or layout.get("layoutid"))
    campaign_id = int(layout.get("campaignId") or layout.get("campaignid") or published_layout_id)

    draft = client.resolve_draft_layout(published_layout_id)
    draft_layout_id = int(draft.get("layoutId") or draft.get("layoutid") or 0)
    client.clear_regions(draft_layout_id)

    try:
        client.edit_layout(draft_layout_id, duration=layout_duration, tags=tags)
    except Exception as exc:  # noqa: BLE001 — soft failure on tags/duration
        LOG.warning("Could not set draft layout duration/tags (%s); continuing", exc)

    regions_spec = timeline.get("regions") or {}
    if not isinstance(regions_spec, dict):
        raise XiboError("timeline.regions must be a mapping")

    region_playlists: dict[str, int] = {}

    def ensure_region(rname: str, geometry: dict[str, int]) -> int:
        if rname in region_playlists:
            return region_playlists[rname]
        created = client.add_region(
            draft_layout_id,
            width=geometry["width"],
            height=geometry["height"],
            top=geometry["top"],
            left=geometry["left"],
            name=rname,
            z_index=geometry.get("zIndex"),
        )
        refreshed = client.get_layout(layout_id=draft_layout_id) or {}
        playlist_id: Optional[int] = client._playlist_id_from_region(created)
        if not playlist_id:
            for region in refreshed.get("regions") or []:
                if str(region.get("name") or "") == rname:
                    playlist_id = client._playlist_id_from_region(region)
                    break
        if not playlist_id:
            for region in refreshed.get("regions") or []:
                rid = client._playlist_id_from_region(region)
                if rid and rid not in region_playlists.values():
                    playlist_id = rid
                    break
        if not playlist_id:
            raise XiboError(f"Could not resolve playlistId for region {rname!r}")
        region_playlists[rname] = playlist_id
        LOG.info("Region %s -> playlistId=%s", rname, playlist_id)
        return playlist_id

    geometry_map = region_geometry_for_timeline(timeline)
    for region_name, base_geometry in geometry_map.items():
        region = regions_spec.get(region_name)
        if not isinstance(region, dict):
            continue
        widgets = [w for w in (region.get("widgets") or []) if isinstance(w, dict)]
        if not widgets:
            continue
        tracks = assign_overlap_tracks(widgets)
        for track_idx, track_widgets in enumerate(tracks):
            if track_idx == 0:
                rname = region_name
                geom = dict(base_geometry)
            else:
                rname = f"{region_name}-overlay-{track_idx}"
                geom = dict(base_geometry)
                geom["zIndex"] = int(base_geometry.get("zIndex") or 0) + track_idx
            playlist_id = ensure_region(rname, geom)
            fill_playlist_from_widgets(
                client,
                playlist_id,
                track_widgets,
                media_ids=resolved_media,
                layout_duration=layout_duration,
            )

    parent_id = int(draft.get("parentId") or published_layout_id)
    published = client.publish_layout(parent_id)
    final_layout_id = parent_id
    published_layout = client.get_layout(layout_id=final_layout_id) or {}
    published_campaign = published.get("campaignId") or published.get("campaignid")
    if published_campaign not in (None, "", 0, "0"):
        campaign_id = int(published_campaign)
    else:
        campaign_id = int(
            published_layout.get("campaignId")
            or published_layout.get("campaignid")
            or campaign_id
        )

    LOG.info(
        "Published layout %s parentId=%s campaignId=%s duration=%ss",
        name,
        final_layout_id,
        campaign_id,
        layout_duration,
    )
    return {
        "layout_name": name,
        "layout_id": final_layout_id,
        "campaign_id": campaign_id,
        "draft_layout_id": draft_layout_id,
        "media_ids": resolved_media,
        "layout_duration": layout_duration,
        "timeline_path": str(path),
        "regions": list(region_playlists),
        "dry_run": False,
    }
