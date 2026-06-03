# V7.0.0 - Multi-Frame support

## Highlights

- **Multi-Frame TV support**: Each Frame TV now writes its thumbnails to a per-TV subdirectory, so multi-Frame setups no longer overwrite each other's `current.jpg`. Each TV also gains three auto-created folder sensors (`sensor.<tv>_personal` / `_store` / `_other`) exposing folder size and a `file_list` attribute for gallery cards.
- **Generation-aware slideshow / auto-rotation** (resolves #18): the integration detects whether each Frame speaks `slideshow_status` (2024+) or `auto_rotation_status` (older ≈2020–2021 models) and routes to it automatically. `art_set_slideshow` and `art_set_auto_rotation` are now functional aliases that work on any model.
- **Reduced WebSocket traffic**: the expensive `get_content_list` call is now throttled to a configurable interval (default 5 minutes, was 15 seconds).
- **Persistent capability detection**: brightness and color-temperature TV support is now learned once and remembered across restarts, removing the per-startup probe delay on TVs (like Frame 2024) that don't implement the dedicated requests.
- **Repairs alert on auth failure**: when the SmartThings OAuth token can no longer be refreshed, a translatable issue is raised in Settings → Repairs with remediation steps, and cleared automatically when auth recovers.
- **Thumbnail fallback**: when a live thumbnail fetch fails, a previously-downloaded copy is reused instead of an error placeholder (contributed by @prestonmcafee).

## What changed for users

### Thumbnail folder layout

**Before V7** (single-Frame friendly only):
```
www/frame_art/
  current.jpg
  MY_F0001.jpg, MY_F0002.jpg, ...
  personal/, store/, other/   (subdirs from manual service calls)
```

**V7** (multi-Frame friendly):
```
www/frame_art/
  {entry_id}/                 (one per config entry / TV)
    current.jpg
    personal/MY_F*.jpg
    store/SAM-*.jpg
    other/
```

The `entry_id` is a 32-character hex string. To find yours, open Developer Tools -> States and look at the `sensor.<tv_name>_frame_art` entity. Two new attributes have been added:

- `entry_id` - the unique identifier for this TV
- `thumbnail_folder` - the full `/local/...` path you can use in Lovelace cards

### Post-migration checklist

After upgrading, three things in your configuration may need updating because they reference the old flat path. Use the `entry_id` attribute exposed on the `sensor.<tv_name>_frame_art` entity (Developer Tools -> States) to find your per-TV identifier.

**1. Lovelace gallery cards** (the bundled `folder-gallery-card.js` or any `custom:folder-gallery-card`):

```yaml
# Before
type: custom:folder-gallery-card
folder: /local/frame_art/personal

# After (replace YOUR_ENTRY_ID with the value from the sensor attribute)
type: custom:folder-gallery-card
folder: /local/frame_art/YOUR_ENTRY_ID/personal
```

**2. `local_file` cameras** declared in `configuration.yaml`:

```yaml
# Before
camera:
  - platform: local_file
    name: Frame art Thumbnail
    file_path: /config/www/frame_art/current.jpg

# After
camera:
  - platform: local_file
    name: Frame art Thumbnail
    file_path: /config/www/frame_art/YOUR_ENTRY_ID/current.jpg
```

**3. `folder` sensors** (the HA `folder` integration, if you've added one to watch the thumbnail directory):

```yaml
# Before
sensor:
  - platform: folder
    folder: /config/www/frame_art

# After
sensor:
  - platform: folder
    folder: /config/www/frame_art/YOUR_ENTRY_ID
```

Note that HA may require you to allowlist the new path under `homeassistant.allowlist_external_dirs` if you had the old one allowlisted.

After updating, restart Home Assistant and the warnings about missing `/config/www/frame_art/current.jpg` will stop.

### Automatic migration

Single-Frame installs upgrading to V7 are migrated automatically on first start:

- existing `www/frame_art/current.jpg` is moved into the new subdirectory
- existing `www/frame_art/personal/`, `store/`, `other/` directories are moved
- the DRM placeholder marker (if present) is moved as well

This runs once. Subsequent starts are no-ops. If migration fails for any reason (permissions, etc.) a `WARNING` is logged and existing files are left in place - you can move them manually.

If you have multiple Frame TVs already configured, only the first config entry will receive the migrated files. The others will start with empty per-TV directories that fill up as artworks change on each TV.

### New advanced option

A new field has been added to the advanced options screen:

- **Frame Art: content list refresh interval (seconds)** - default 300 (5 min). Lower values keep the gallery counter fresher at the cost of more WebSocket traffic; higher values reduce TV load. Range 30-3600.

The Frame Art sensor itself still refreshes every 15 seconds for cheap state (current artwork, slideshow status, art mode). Only the full content list (which lists every saved artwork on the TV) is throttled to this longer cycle.

### Generation-aware slideshow / auto-rotation (resolves #18)

Samsung Frame TVs don't all expose the same slideshow API. Newer models (2024+, `…LS03D…` and later) answer `slideshow_status`; older models (≈2020–2021, `…LS03T…`, `…LS03A…`) only answer the parallel `auto_rotation_status`. Previously, older Frames silently failed to start or report a slideshow.

V7 detects which API each TV speaks (probing once and persisting the result in the config entry) and routes all reads and writes to it. As a result:

- `art_set_slideshow` and `art_set_auto_rotation` are now functional **aliases** — either works on any Frame model; the integration sends the request to whichever API the TV actually responds to.
- `slideshow_status` is now reported correctly on older Frames.
- The `duration` field accepts custom integer-minute values (e.g. `30`, `45`, `180`) in addition to the presets `3min`, `15min`, `1h`, `12h`, `1d`, `7d`. Models that reject a duration now log it instead of failing silently.

Thanks to @prestonmcafee for the multi-generation testing (2020 / 2021 / 2024) behind this fix.

### Authentication failure now shows in Repairs

When the SmartThings OAuth token can't be refreshed (revoked, expired, or rotated server-side), the integration raises a translatable issue in **Settings → Repairs** explaining the cause and pointing to the reconfigure flow. The issue is cleared automatically once a refresh succeeds. Available in en, fr, es, it, hu, pt-BR.

### Thumbnail fallback

If a live thumbnail fetch fails after retries, the integration now reuses a previously-downloaded copy of the same artwork (from `personal/`, `store/`, or `other/`) as `current.jpg` instead of writing an error placeholder. Contributed by @prestonmcafee.

## Breaking changes

The thumbnail folder layout changed from flat to per-TV. Anything in your HA configuration that references `/config/www/frame_art/` (or `/local/frame_art/` for URLs) needs to be updated to include the per-TV `entry_id`. See the post-migration checklist above. Specifically affected:

- Lovelace cards (gallery card or any other card displaying thumbnails)
- `local_file` camera entities in `configuration.yaml`
- `folder` sensor entities in `configuration.yaml`

## Bug fixes carried forward from 6.13.x

- Fix issue #12 (excprocess): Art WebSocket would stay stuck on a dead transport after TV standby until manual reload (6.13.2).
- Fix issue #13 (azebro): repeated "Allow device" prompts on Frame 2024 firmware. Token is now sent on all WS channels (6.13.4).
- REST URL port is no longer hard-coded.

## Acknowledgements

Special thanks to **@prestonmcafee** for the detailed, multi-generation testing behind this release. Running 2020, 2021, and 2024 Frame TVs side by side, he provided per-model state dumps, firmware versions, and methodical before/after logs that pinpointed the slideshow API split (#18), the `art_mode_changed`-without-request-id confirmation on older Frames (Art Mode activation fix), and suggested the cached-thumbnail fallback for `current.jpg`.

