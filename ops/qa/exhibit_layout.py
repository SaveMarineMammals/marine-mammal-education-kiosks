"""Build and publish multi-region Xibo layouts from exhibit timeline.yaml."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Protocol

from pathutil import resolve_manifest_path

LOG = logging.getLogger("xibo_qa.exhibit_layout")

REPO_ROOT = Path(__file__).resolve().parents[2]
EXHIBITS_DIR = REPO_ROOT / "exhibits"

# layered-stills-loop region geometry
LAYERED_STILLS_REGIONS: dict[str, dict[str, int]] = {
    "background": {"left": 0, "top": 0, "width": 1920, "height": 1080, "zIndex": 0},
    "midground": {"left": 0, "top": 0, "width": 1920, "height": 1080, "zIndex": 1},
    "text": {"left": 160, "top": 720, "width": 1600, "height": 280, "zIndex": 2},
    "accent": {"left": 1580, "top": 40, "width": 280, "height": 280, "zIndex": 3},
}


class PipelineError(RuntimeError):
    """Fatal layout publish failure."""


class XiboLayoutClient(Protocol):
    def upload_media(self, file_path: Path, name: Optional[str] = None) -> int: ...

    def create_layout(self, name: str, width: int = 1920, height: int = 1080) -> dict[str, Any]: ...

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

    def add_text_widget(self, playlist_id: int, text: str, duration: int) -> int: ...

    def publish_layout(self, layout_id: int) -> dict[str, Any]: ...


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise PipelineError(
            "PyYAML is required: pip install -r ops/qa/requirements.txt"
        ) from exc
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise PipelineError(f"YAML root must be a mapping: {path}")
    return data


def timeline_path_for(slug: str) -> Path:
    return EXHIBITS_DIR / slug / "layouts" / "timeline.yaml"


def _local_paths_for_asset(exhibit_dir: Path, asset: dict[str, Any]) -> list[Path]:
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


def resolve_asset_upload_path(
    exhibit_dir: Path,
    asset: dict[str, Any],
    *,
    widget_type: str,
) -> Path:
    """Resolve a local file to upload. HTML packages prefer ``.zip`` (uploaded as ``.htz``)."""
    filename = str(asset.get("filename") or "").strip()
    uri = str(asset.get("uri") or "").strip()
    candidates: list[Path] = []

    if widget_type == "html-package":
        # Prefer zip/htz package; CMS upload renames zip → htz.
        for ext in (".zip", ".htz"):
            if filename.endswith(".zip") or filename.endswith(".htz"):
                stem = Path(filename).stem
                candidates.append(exhibit_dir / "media" / "assets" / f"{stem}{ext}")
            elif filename:
                stem = Path(filename).stem
                candidates.append(exhibit_dir / "media" / "assets" / f"{stem}{ext}")
        if uri:
            resolved = resolve_manifest_path(uri, root=REPO_ROOT)
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

    raise PipelineError(
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


def prepare_timeline_for_qa(
    timeline: dict[str, Any],
    *,
    image_only: bool = False,
    skip_html_packages: bool = False,
) -> dict[str, Any]:
    """Filter timeline for headless player QA (bisect / WebKit quarantine).

    - ``image_only``: single background region with the first image widget only
      (isolates RegionImpl paint from text/HTML/multi-region).
    - ``skip_html_packages``: drop ``html-package`` widgets so image+text still
      validate under Xvfb when WebKitGTK segfaults.
    """
    import copy

    filtered = copy.deepcopy(timeline)
    regions = filtered.get("regions")
    if not isinstance(regions, dict):
        return filtered

    if image_only:
        first_image: Optional[dict[str, Any]] = None
        for region_name in ("background", "midground", "accent", "text"):
            region = regions.get(region_name)
            if not isinstance(region, dict):
                continue
            for widget in region.get("widgets") or []:
                if not isinstance(widget, dict):
                    continue
                wtype = str(widget.get("type") or "").strip()
                if wtype in {"image", ""} and widget.get("asset"):
                    first_image = dict(widget)
                    first_image["type"] = "image"
                    first_image["startSeconds"] = 0
                    break
            if first_image is not None:
                break
        if first_image is None:
            raise PipelineError("QA image_only layout needs at least one image widget")
        duration = int(filtered.get("durationSeconds") or 90)
        first_image["durationSeconds"] = duration
        filtered["regions"] = {
            "background": {
                "widgets": [first_image],
            }
        }
        LOG.info(
            "QA image_only layout: asset=%s duration=%ss",
            first_image.get("asset"),
            duration,
        )
        return filtered

    if skip_html_packages:
        dropped = 0
        for region_name, region in list(regions.items()):
            if not isinstance(region, dict):
                continue
            widgets = region.get("widgets") or []
            kept = [
                w
                for w in widgets
                if isinstance(w, dict) and str(w.get("type") or "").strip() != "html-package"
            ]
            dropped += len(widgets) - len(kept)
            if kept:
                region["widgets"] = kept
            else:
                del regions[region_name]
        if dropped:
            LOG.info("QA skip_html_packages: dropped %s html-package widget(s)", dropped)
    return filtered


def upload_timeline_assets(
    client: XiboLayoutClient,
    *,
    slug: str,
    timeline: dict[str, Any],
) -> dict[str, int]:
    exhibit_dir = EXHIBITS_DIR / slug
    manifest = load_yaml(exhibit_dir / "media" / "manifest.yaml")
    assets_by_id: dict[str, dict[str, Any]] = {}
    for asset in manifest.get("assets") or []:
        if isinstance(asset, dict) and asset.get("id"):
            assets_by_id[str(asset["id"])] = asset

    media_ids: dict[str, int] = {}
    for _region, widget in collect_timeline_widgets(timeline):
        wtype = str(widget.get("type") or "").strip()
        if wtype == "text":
            continue
        asset_id = str(widget.get("asset") or "").strip()
        if not asset_id or asset_id in media_ids:
            continue
        asset = assets_by_id.get(asset_id)
        if asset is None:
            raise PipelineError(f"timeline references unknown asset id={asset_id!r}")
        path = resolve_asset_upload_path(exhibit_dir, asset, widget_type=wtype or "image")
        media_ids[asset_id] = client.upload_media(path, name=f"{slug}-{asset_id}")
    LOG.info("Uploaded %s timeline assets for exhibit=%s", len(media_ids), slug)
    return media_ids


def _widget_window(widget: dict[str, Any]) -> tuple[float, float]:
    start = float(widget.get("startSeconds") or 0)
    duration = float(widget.get("durationSeconds") or 0)
    return start, start + max(duration, 0)


def assign_overlap_tracks(widgets: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Greedy interval coloring: concurrent widgets go on separate tracks."""
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
    """Map absolute-timed widgets onto a sequential Xibo playlist with spacers."""
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
            client.add_text_widget(playlist_id, copy, duration)
        elif wtype in {"image", "html-package", ""}:
            asset_id = str(widget.get("asset") or "").strip()
            media_id = media_ids.get(asset_id)
            if media_id is None:
                raise PipelineError(f"No uploaded media for asset {asset_id!r}")
            client.assign_media_to_playlist(playlist_id, media_id, duration=duration)
        else:
            raise PipelineError(f"Unsupported timeline widget type: {wtype!r}")
        cursor = max(cursor, start) + duration

    trailing = int(round(layout_duration - cursor))
    if trailing >= 1:
        client.add_spacer_widget(playlist_id, trailing)


def publish_exhibit_layout(
    client: XiboLayoutClient,
    *,
    exhibit_slug: str,
    layout_name: str,
    image_only: bool = False,
    skip_html_packages: bool = False,
) -> dict[str, Any]:
    """Build multi-region layout from timeline.yaml, publish, return metadata."""
    path = timeline_path_for(exhibit_slug)
    if not path.is_file():
        raise PipelineError(f"Missing timeline for exhibit publish: {path}")

    timeline = prepare_timeline_for_qa(
        load_yaml(path),
        image_only=image_only,
        skip_html_packages=skip_html_packages,
    )
    layout_duration = int(timeline.get("durationSeconds") or 90)
    media_ids = upload_timeline_assets(client, slug=exhibit_slug, timeline=timeline)

    layout = client.create_layout(layout_name)
    published_layout_id = int(layout.get("layoutId") or layout.get("layoutid"))
    campaign_id = int(layout.get("campaignId") or layout.get("campaignid") or published_layout_id)

    draft = client.resolve_draft_layout(published_layout_id)
    draft_layout_id = int(draft.get("layoutId") or draft.get("layoutid") or 0)
    client.clear_regions(draft_layout_id)

    try:
        client.edit_layout(draft_layout_id, duration=layout_duration)
    except Exception as exc:  # noqa: BLE001 — client raises PipelineError subclass
        LOG.warning("Could not set draft layout duration (%s); continuing", exc)

    regions_spec = timeline.get("regions") or {}
    if not isinstance(regions_spec, dict):
        raise PipelineError("timeline.regions must be a mapping")

    region_playlists: dict[str, int] = {}

    def ensure_region(name: str, geometry: dict[str, int]) -> int:
        if name in region_playlists:
            return region_playlists[name]
        created = client.add_region(
            draft_layout_id,
            width=geometry["width"],
            height=geometry["height"],
            top=geometry["top"],
            left=geometry["left"],
            name=name,
            z_index=geometry.get("zIndex"),
        )
        refreshed = client.get_layout(layout_id=draft_layout_id) or {}
        playlist_id: Optional[int] = client._playlist_id_from_region(created)
        if not playlist_id:
            for region in refreshed.get("regions") or []:
                if str(region.get("name") or "") == name:
                    playlist_id = client._playlist_id_from_region(region)
                    break
        if not playlist_id:
            for region in refreshed.get("regions") or []:
                rid = client._playlist_id_from_region(region)
                if rid and rid not in region_playlists.values():
                    playlist_id = rid
                    break
        if not playlist_id:
            raise PipelineError(f"Could not resolve playlistId for region {name!r}")
        region_playlists[name] = playlist_id
        LOG.info("Region %s -> playlistId=%s", name, playlist_id)
        return playlist_id

    midground_geometry = LAYERED_STILLS_REGIONS["midground"]
    for region_name in ("background", "midground", "text", "accent"):
        region = regions_spec.get(region_name)
        if not isinstance(region, dict):
            continue
        widgets = [w for w in (region.get("widgets") or []) if isinstance(w, dict)]
        if not widgets:
            continue

        if region_name == "midground":
            tracks = assign_overlap_tracks(widgets)
            for track_idx, track_widgets in enumerate(tracks):
                if track_idx == 0:
                    rname = "midground"
                    geom = dict(midground_geometry)
                else:
                    rname = f"midground-overlay-{track_idx}"
                    geom = dict(midground_geometry)
                    geom["zIndex"] = midground_geometry["zIndex"] + track_idx
                playlist_id = ensure_region(rname, geom)
                fill_playlist_from_widgets(
                    client,
                    playlist_id,
                    track_widgets,
                    media_ids=media_ids,
                    layout_duration=layout_duration,
                )
            continue

        geometry = LAYERED_STILLS_REGIONS.get(region_name)
        if geometry is None:
            raise PipelineError(f"No geometry for region {region_name!r}")
        playlist_id = ensure_region(region_name, geometry)
        fill_playlist_from_widgets(
            client,
            playlist_id,
            widgets,
            media_ids=media_ids,
            layout_duration=layout_duration,
        )

    parent_id = int(draft.get("parentId") or published_layout_id)
    published = client.publish_layout(parent_id)
    # Publish retires the draft; the stable published id remains the parent.
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
        "Published exhibit layout parentId=%s campaignId=%s duration=%ss regions=%s",
        final_layout_id,
        campaign_id,
        layout_duration,
        list(region_playlists),
    )
    return {
        "layout_id": final_layout_id,
        "campaign_id": campaign_id,
        "draft_layout_id": draft_layout_id,
        "media_ids": media_ids,
        "layout_duration": layout_duration,
        "timeline_path": str(path),
        "regions": list(region_playlists),
        "image_only": image_only,
        "skip_html_packages": skip_html_packages,
    }
