# Release notes — 8.2.0 (since 8.1.0)

> **Status: pre-release (beta).** 8.2.0 builds on 8.1.0.

## Folder Gallery card — per-gallery action buttons (`gallery_type`)

- **New `gallery_type` option** to force the fullscreen-preview action buttons
  for a whole gallery, instead of guessing per image:
  - `personal` → **Select** + **Delete**
  - `favorites` → **Select** + **Unfavourite**
  - `upload` → **Upload**
  - omitted / `auto` → detect per image from the content-id prefix (previous
    behaviour). Also available as a dropdown in the visual editor. Useful for an
    upload folder of plain photos, which would otherwise be guessed per file.

## Folder Gallery card — more options in the visual editor

- The card's visual editor now exposes, in addition to the basic fields:
  - **Server-side thumbnails** (checkbox) and **Thumbnail width** (px).
  - **Actions** for single tap / double tap / long press, each a simple
    dropdown (*Open preview / Display on TV / Nothing*), plus a **Frame TV
    entity** field used to build the "Display on TV" action. No need to hand-
    write the YAML action objects anymore for the common setup.

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
