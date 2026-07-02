# Release notes — 8.2.0 (since 8.1.0)

> **Status: pre-release (beta).** 8.2.0 builds on 8.1.0.

## Picture mode select — no longer reverts to the old mode after a change

- **Setting the picture mode (e.g. via `select.select_option` or the Picture
  Mode select) no longer snaps back to the previous value.** SmartThings lags
  ~30-45s before it reports the new mode, but the select only skipped polling
  for 5s — so the next poll read the *old* mode from the cloud and reverted the
  selection (issue #116). The select now **holds the mode you set until the
  cloud confirms it** (60s grace window); if the cloud still hasn't confirmed
  after that, it accepts the cloud's value, so a change made on the TV itself is
  still reflected.

## Folder Gallery card — translations (FR, ES, IT, pt-BR, HU) + required Frame TV entity

- **The card is now translated** into French, Spanish, Italian, Brazilian
  Portuguese and Hungarian (with English as the fallback). This covers the
  visual editor (labels, hints, gallery-type and gesture dropdowns), the
  fullscreen-preview buttons (Select / Unfavourite / Upload / Delete / Close),
  the Frame chooser, the empty state and the toasts. The language follows Home
  Assistant's UI language (`hass.locale.language`).
- **The visual editor no longer lets you save an action without a Frame TV
  entity.** If a single/double/long-press action is set to Display / Upload /
  Delete / Unfavourite but the **Frame TV entity** field is empty, the card now
  rejects the config (HA shows the error and blocks the save) instead of
  silently saving an action that has no target to run against.

## Folder Gallery card — gesture actions follow the gallery type

- **The tap / double-tap / long-press action dropdowns in the visual editor now
  offer the actions that fit the gallery's `gallery_type`:**
  - `upload` → **Upload to TV**
  - `personal` → **Display on TV** / **Delete**
  - `favorites` → **Display on TV** / **Unfavourite**
  - `auto` → **Display on TV** (generic)

  So e.g. an upload gallery no longer offers "Display on TV" on double-tap/hold —
  it offers **Upload** instead. Each preset builds the matching
  `samsungtv_smart.art_*` action for the configured Frame TV entity. Choosing a
  gallery type re-scopes the gesture options (a now-invalid choice resets to
  "Nothing").

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
