#!/usr/bin/env python3
"""CI-friendly timeline preview: render HTML, screenshot, assert non-black frames.

Does not boot Xibo CMS/Docker. Uses the Chromium timeline preview renderer plus
Playwright for a still capture.

Usage:
  python ops/qa/ci_timeline_preview.py
  python ops/qa/ci_timeline_preview.py --exhibit asian-small-clawed-otters
  python ops/qa/ci_timeline_preview.py --from-git-diff origin/main
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

QA_DIR = Path(__file__).resolve().parent
ROOT = QA_DIR.parents[1]
EXHIBITS = ROOT / "exhibits"
DEFAULT_OUT = QA_DIR / "artifacts" / "timeline-preview-ci"

if str(QA_DIR) not in sys.path:
    sys.path.insert(0, str(QA_DIR))
if str(QA_DIR / "timeline_preview") not in sys.path:
    sys.path.insert(0, str(QA_DIR / "timeline_preview"))

from render_timeline import render_exhibit  # noqa: E402


def discover_exhibits_with_timeline() -> list[str]:
    slugs: list[str] = []
    if not EXHIBITS.is_dir():
        return slugs
    for path in sorted(EXHIBITS.iterdir()):
        if not path.is_dir() or path.name.startswith("_"):
            continue
        if (path / "layouts" / "timeline.yaml").is_file():
            slugs.append(path.name)
    return slugs


def exhibits_from_git_diff(base_ref: str) -> list[str]:
    """Return exhibit slugs touched under layouts/ or media/ vs base_ref."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"warning: git diff failed ({exc}); validating all exhibits", file=sys.stderr)
        return discover_exhibits_with_timeline()

    slugs: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.strip().replace("\\", "/").split("/")
        if len(parts) >= 2 and parts[0] == "exhibits":
            slug = parts[1]
            if slug.startswith("_"):
                continue
            # Layout/media changes, or any change under an exhibit that has a timeline.
            if len(parts) >= 3 and parts[2] in {"layouts", "media"}:
                slugs.add(slug)
            elif (EXHIBITS / slug / "layouts" / "timeline.yaml").is_file():
                # Framework/template changes handled by caller forcing all; skip here.
                pass
    # If framework / preview tooling changed, preview every timeline exhibit.
    for line in proc.stdout.splitlines():
        norm = line.strip().replace("\\", "/")
        if (
            norm.startswith("framework/layout-templates/")
            or norm.startswith("ops/qa/timeline_preview/")
            or norm == "ops/qa/exhibit_layout.py"
            or norm == "ops/qa/ci_timeline_preview.py"
        ):
            return discover_exhibits_with_timeline()

    return sorted(
        s for s in slugs if (EXHIBITS / s / "layouts" / "timeline.yaml").is_file()
    )


def region_names(slug: str) -> list[str]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML required") from exc
    path = EXHIBITS / slug / "layouts" / "timeline.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    regions = (data or {}).get("regions") or {}
    if not isinstance(regions, dict):
        return []
    return list(regions.keys())


def capture_still(index_html: Path, still_path: Path, *, width: int, height: int) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required for CI preview: pip install playwright && playwright install chromium"
        ) from exc

    uri = index_html.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(uri, wait_until="networkidle")
        # Let the preview clock advance slightly so widgets paint.
        page.wait_for_timeout(1200)
        page.screenshot(path=str(still_path), full_page=False)
        browser.close()


def frame_is_non_black(still_path: Path, *, min_nonzero_ratio: float = 0.01) -> tuple[bool, dict[str, Any]]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Pillow is required: pip install Pillow") from exc

    with Image.open(still_path) as im:
        rgb = im.convert("RGB")
        width, height = rgb.size
        pixels = list(rgb.getdata())
    total = len(pixels) or 1
    nonzero = sum(1 for r, g, b in pixels if r > 8 or g > 8 or b > 8)
    ratio = nonzero / total
    stats = {
        "width": width,
        "height": height,
        "nonzero_ratio": round(ratio, 4),
        "min_nonzero_ratio": min_nonzero_ratio,
    }
    return ratio >= min_nonzero_ratio, stats


def preview_one(slug: str, out_root: Path) -> dict[str, Any]:
    exhibit_out = out_root / slug
    exhibit_out.mkdir(parents=True, exist_ok=True)
    regions = region_names(slug)
    result: dict[str, Any] = {
        "slug": slug,
        "regions": regions,
        "ok": False,
        "errors": [],
    }
    if not regions:
        result["errors"].append("timeline.regions is empty")
        return result

    try:
        meta = render_exhibit(slug, out_dir=exhibit_out / "html", record_duration=2, show_hud=False)
    except (OSError, FileNotFoundError, SystemExit) as exc:
        result["errors"].append(str(exc))
        return result

    index_html = Path(meta["index_html"])
    still_path = exhibit_out / "still.png"
    width = 1920
    height = 1080
    try:
        capture_still(index_html, still_path, width=width, height=height)
    except Exception as exc:  # noqa: BLE001 — surface capture failures in report
        result["errors"].append(f"screenshot failed: {exc}")
        return result

    ok_frame, stats = frame_is_non_black(still_path)
    result["still"] = str(still_path.relative_to(ROOT)).replace("\\", "/")
    result["frame"] = stats
    if not ok_frame:
        result["errors"].append(
            f"capture looks black/empty (nonzero_ratio={stats['nonzero_ratio']})"
        )
        return result

    result["ok"] = True
    result["template"] = meta.get("template")
    return result


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhibit", action="append", help="Exhibit slug (repeatable)")
    parser.add_argument(
        "--from-git-diff",
        metavar="BASE_REF",
        help="Only exhibits touched vs this git ref (layouts/media) or all if framework/preview changed",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output directory (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args(argv)

    if args.exhibit:
        slugs = list(dict.fromkeys(args.exhibit))
    elif args.from_git_diff:
        slugs = exhibits_from_git_diff(args.from_git_diff)
        if not slugs:
            print("OK: no timeline exhibits affected by diff; skipping preview")
            report = {
                "ok": True,
                "skipped": True,
                "exhibits": [],
                "message": "no timeline exhibits in diff",
            }
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / "qa-report.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            return 0
    else:
        slugs = discover_exhibits_with_timeline()

    if not slugs:
        print("error: no exhibits with layouts/timeline.yaml found", file=sys.stderr)
        return 1

    out_root = args.out
    out_root.mkdir(parents=True, exist_ok=True)
    results = [preview_one(slug, out_root) for slug in slugs]
    failed = [r for r in results if not r.get("ok")]
    report = {
        "ok": not failed,
        "skipped": False,
        "renderer": "timeline-preview-ci",
        "exhibits": results,
    }
    report_path = out_root / "qa-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

    if failed:
        print(f"FAILED: {len(failed)}/{len(results)} exhibit preview(s)", file=sys.stderr)
        return 1
    print(f"OK: {len(results)} exhibit preview(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
