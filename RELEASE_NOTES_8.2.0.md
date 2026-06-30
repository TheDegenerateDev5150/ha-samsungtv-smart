# Release notes — 8.2.0 (since 8.1.0)

> **Status: pre-release (beta).** 8.2.0 builds on 8.1.0.

## Folder Gallery card — server-side resized thumbnails for big folders

- **The gallery now loads small resized thumbnails instead of the originals.**
  Pointing the card at a folder of full-size photos (several MB each, many of
  them) used to make the browser download and decode every original at full
  resolution just to render the grid — slow, memory-heavy, and visually poor.
  The integration now exposes an on-demand thumbnail endpoint
  (`/api/samsungtv_smart/thumbnail`) that returns a small cached JPEG (resized
  with Pillow, cached on disk keyed by file + size + mtime). The card points
  its grid images there, so only kilobytes per tile reach the browser; the
  full-resolution original is still used for the lightbox and tap/hold actions.

  - Enabled by default. Disable per card with `server_thumbnails: false`.
  - Tune the size with `thumbnail_width:` (default `400`).
  - Only local files (`/local/...`) are routed through the resizer; remote URLs
    are used as-is. If Pillow isn't available, the endpoint transparently falls
    back to the original image.
  - The endpoint only ever reads files under `<config>/www` (already public at
    `/local/`) and validates the path against traversal.
