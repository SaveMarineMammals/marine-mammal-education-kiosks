#!/usr/bin/env python3
"""Render exhibits/<slug>/layouts/timeline.yaml into a Chromium-ready preview.

Writes a self-contained page under an output directory (typically the QA
player-runtime bind mount) so the headless container can open:

  file:///var/lib/xibo-player/timeline-preview/index.html
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[3]  # repo root
QA_DIR = Path(__file__).resolve().parents[1]  # ops/qa
EXHIBITS = ROOT / "exhibits"
STATIC_DIR = Path(__file__).resolve().parent

# ops/qa on sys.path so pathutil resolves the same way as the pipeline.
if str(QA_DIR) not in sys.path:
    sys.path.insert(0, str(QA_DIR))
from pathutil import resolve_manifest_path  # noqa: E402


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit(
            "PyYAML is required: pip install -r ops/qa/requirements.txt"
        ) from exc
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"YAML root must be a mapping: {path}")
    return data


def asset_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for asset in manifest.get("assets") or []:
        if isinstance(asset, dict) and asset.get("id"):
            out[str(asset["id"])] = asset
    return out


def resolve_asset_file(exhibit_dir: Path, asset: dict[str, Any]) -> Optional[Path]:
    uri = str(asset.get("uri") or "").strip()
    candidates: list[Path] = []
    if uri:
        candidates.append(resolve_manifest_path(uri, root=ROOT))
    filename = str(asset.get("filename") or "").strip()
    if filename:
        candidates.append(exhibit_dir / "media" / "assets" / filename)
        # Prefer loose HTML over zip when both exist for html-package accents.
        if filename.endswith(".zip"):
            candidates.insert(0, exhibit_dir / "media" / "assets" / filename.replace(".zip", ".html"))
    for path in candidates:
        if path.is_file():
            return path
    return None


def copy_media(src: Path, media_dir: Path) -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    dest = media_dir / src.name
    if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
        shutil.copy2(src, dest)
    return f"media/{dest.name}"


def transition_class(name: str) -> str:
    key = (name or "none").strip()
    if key in {"fade", "fadeIn", "none", ""}:
        return ""
    return f" from-{key}"


def render_image_widget(widget: dict[str, Any], rel_src: str) -> str:
    wid = widget.get("id") or "img"
    start = float(widget.get("startSeconds") or 0)
    duration = float(widget.get("durationSeconds") or 0)
    tin = widget.get("transitionIn") or "none"
    tout = widget.get("transitionOut") or "none"
    tms = int(widget.get("transitionDurationMs") or 600)
    return (
        f'<div class="widget img-widget{transition_class(str(tin))}" data-widget '
        f'data-id="{_esc(str(wid))}" data-start="{start}" data-duration="{duration}" '
        f'data-transition-in="{_esc(str(tin))}" data-transition-out="{_esc(str(tout))}" '
        f'data-transition-ms="{tms}">'
        f'<img src="{_esc(rel_src)}" alt="{_esc(str(wid))}" draggable="false"/>'
        f"</div>"
    )


def render_text_widget(widget: dict[str, Any]) -> str:
    wid = widget.get("id") or "text"
    start = float(widget.get("startSeconds") or 0)
    duration = float(widget.get("durationSeconds") or 0)
    tin = widget.get("transitionIn") or "fade"
    tout = widget.get("transitionOut") or "fade"
    tms = int(widget.get("transitionDurationMs") or 600)
    effect = widget.get("effect") or "none"
    copy = str(widget.get("copy") or "").strip()
    effect_class = f" effect-{effect}" if effect and effect != "none" else ""
    return (
        f'<div class="widget text-widget{effect_class}{transition_class(str(tin))}" data-widget '
        f'data-id="{_esc(str(wid))}" data-start="{start}" data-duration="{duration}" '
        f'data-transition-in="{_esc(str(tin))}" data-transition-out="{_esc(str(tout))}" '
        f'data-transition-ms="{tms}">'
        f'<div class="scrim">{_esc(copy)}</div>'
        f"</div>"
    )


def render_html_widget(widget: dict[str, Any], rel_src: str) -> str:
    wid = widget.get("id") or "html"
    start = float(widget.get("startSeconds") or 0)
    duration = float(widget.get("durationSeconds") or 0)
    return (
        f'<iframe class="accent-frame widget" data-widget data-id="{_esc(str(wid))}" '
        f'data-start="{start}" data-duration="{duration}" '
        f'data-transition-in="none" data-transition-out="none" data-transition-ms="0" '
        f'src="{_esc(rel_src)}" title="{_esc(str(wid))}"></iframe>'
    )


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_layer_html(
    *,
    region_name: str,
    region: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    exhibit_dir: Path,
    media_dir: Path,
) -> str:
    widgets = region.get("widgets") or []
    parts: list[str] = []
    for widget in widgets:
        if not isinstance(widget, dict):
            continue
        wtype = str(widget.get("type") or "").strip()
        if wtype == "text":
            parts.append(render_text_widget(widget))
            continue

        asset_id = str(widget.get("asset") or "").strip()
        asset = assets.get(asset_id)
        if asset is None:
            print(f"warning: missing asset {asset_id!r} for widget {widget.get('id')}", file=sys.stderr)
            continue
        src = resolve_asset_file(exhibit_dir, asset)
        if src is None:
            print(f"warning: no local file for asset {asset_id!r}", file=sys.stderr)
            continue
        rel = copy_media(src, media_dir)

        if wtype in {"image", ""}:
            parts.append(render_image_widget(widget, rel))
        elif wtype == "html-package":
            # Prefer .html sibling when we copied from zip path resolution.
            if not rel.endswith(".html"):
                html_sib = exhibit_dir / "media" / "assets" / (asset_id + ".html")
                if not html_sib.is_file():
                    fname = str(asset.get("filename") or "")
                    if fname.endswith(".zip"):
                        html_sib = exhibit_dir / "media" / "assets" / fname.replace(".zip", ".html")
                if html_sib.is_file():
                    rel = copy_media(html_sib, media_dir)
            parts.append(render_html_widget(widget, rel))
        else:
            parts.append(render_image_widget(widget, rel))

    return f'<div class="layer" id="layer-{_esc(region_name)}">{"".join(parts)}</div>'


def render_exhibit(
    slug: str,
    *,
    out_dir: Path,
    record_duration: Optional[int] = None,
    show_hud: bool = True,
) -> dict[str, Any]:
    exhibit_dir = EXHIBITS / slug
    timeline_path = exhibit_dir / "layouts" / "timeline.yaml"
    manifest_path = exhibit_dir / "media" / "manifest.yaml"
    if not timeline_path.is_file():
        raise FileNotFoundError(f"Missing timeline: {timeline_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    timeline = load_yaml(timeline_path)
    manifest = load_yaml(manifest_path)
    assets = asset_index(manifest)

    loop_seconds = int(timeline.get("durationSeconds") or 90)
    loop = bool(timeline.get("loop", True))
    record = int(record_duration) if record_duration is not None else loop_seconds
    resolution = timeline.get("resolution") or {}
    width = int(resolution.get("width") or 1920)
    height = int(resolution.get("height") or 1080)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    media_dir = out_dir / "media"

    shutil.copy2(STATIC_DIR / "player.css", out_dir / "player.css")
    shutil.copy2(STATIC_DIR / "player.js", out_dir / "player.js")

    regions = timeline.get("regions") or {}
    layer_order = ("background", "midground", "text", "accent")
    layers_html: list[str] = []
    for name in layer_order:
        region = regions.get(name)
        if not isinstance(region, dict):
            layers_html.append(f'<div class="layer" id="layer-{name}"></div>')
            continue
        layers_html.append(
            build_layer_html(
                region_name=name,
                region=region,
                assets=assets,
                exhibit_dir=exhibit_dir,
                media_dir=media_dir,
            )
        )

    preview_cfg = {
        "slug": slug,
        "durationSeconds": loop_seconds,
        "recordDuration": record,
        "loop": loop,
        "width": width,
        "height": height,
    }
    hud = '<div id="hud">t=0.0s</div>' if show_hud else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={width}, height={height}, initial-scale=1"/>
<title>QA timeline preview — {_esc(slug)}</title>
<link rel="stylesheet" href="player.css"/>
<script>window.TIMELINE_PREVIEW = {json.dumps(preview_cfg)};</script>
</head>
<body>
<div id="stage" style="width:{width}px;height:{height}px">
{hud}
{"".join(layers_html)}
</div>
<script src="player.js"></script>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    meta = {
        "slug": slug,
        "timeline_path": str(timeline_path),
        "out_dir": str(out_dir),
        "duration_seconds": loop_seconds,
        "record_duration": record,
        "index_html": str(out_dir / "index.html"),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhibit", required=True, help="Exhibit slug under exhibits/")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: ops/qa/player-runtime/timeline-preview)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Recording window seconds injected into the preview clock",
    )
    parser.add_argument("--no-hud", action="store_true", help="Hide on-screen clock HUD")
    args = parser.parse_args(argv)

    out = args.out or (QA_DIR / "player-runtime" / "timeline-preview")
    try:
        meta = render_exhibit(
            args.exhibit,
            out_dir=out,
            record_duration=args.duration,
            show_hud=not args.no_hud,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
