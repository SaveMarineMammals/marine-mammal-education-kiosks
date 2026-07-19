# Layout templates

Reusable Xibo layout patterns. Each subdirectory is a template `id` referenced from `exhibit.yaml` as `layoutTemplate`.

| ID | Description |
| --- | --- |
| [`full-bleed-video`](full-bleed-video/) | Single region, edge-to-edge video |
| [`glance-and-match`](glance-and-match/) | Static hero ID + paging insight cards + CTA ticker |
| [`image-caption`](image-caption/) | Still + lower-third caption |
| [`layered-stills-loop`](layered-stills-loop/) | Multi-region stills + text; motion via transitions (no video) |
| [`html-interactive`](html-interactive/) | HTML widget shell for lightweight interactivity |

Build instances in CMS from these recipes. Do not commit media-heavy layout export ZIPs here.

For a scaled 1080p mockup of each template, see [`../preview/`](../preview/).
