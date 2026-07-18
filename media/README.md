# Local media working directory

Use this tree for **large** masters that belong in the external media store (video, or any file ≥ 2 MB):

```text
media/<exhibit-slug>/masters/
```

This tree is **gitignored**. Upload finished large assets to the media store and record store keys in `exhibits/<slug>/media/manifest.yaml`.

**Images and sound under 2 MB each** should be committed in the exhibit package instead — typically `exhibits/<slug>/media/assets/` — not here. See [docs/architecture.md](../docs/architecture.md).
