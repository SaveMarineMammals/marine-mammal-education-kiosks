# Template: full-bleed-video

## Intent

One composition: edge-to-edge video fills the canvas. Optional short caption only if required for accessibility or learning goals.

## Canvas

- 1920×1080 landscape

## Regions

| Region | Size / position | Content |
| --- | --- | --- |
| video | 1920×1080 @ 0,0 | Library video (`role: hero-video`) |
| caption (optional) | lower third | Text widget from exhibit `copy/` |

## CMS notes

- Prefer native video module; loop per exhibit schedule intent.
- Tag media with `exhibit:<slug>` and `role:hero-video`.
