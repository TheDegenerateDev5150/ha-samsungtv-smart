# V7.0.0 - Multi-Frame support

## Highlights

- **Multi-Frame TV support**: Each Frame TV now writes its thumbnails to a per-TV subdirectory, so multi-Frame setups no longer overwrite each other's `current.jpg`.
- **Reduced WebSocket traffic**: the expensive `get_content_list` call is now throttled to a configurable interval (default 5 minutes, was 15 seconds).
- **Persistent capability detection**: brightness and color-temperature TV support is now learned once and remembered across restarts, removing the per-startup probe delay on TVs (like Frame 2024) that don't implement the dedicated requests.

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

### Lovelace card configuration

If you use the bundled `folder-gallery-card.js`, update the `folder:` option in your card config:

**Before:**
```yaml
type: custom:folder-gallery-card
folder: /local/frame_art/personal
```

**After (replace `YOUR_ENTRY_ID` with your actual entry_id):**
```yaml
type: custom:folder-gallery-card
folder: /local/frame_art/YOUR_ENTRY_ID/personal
```

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

## Breaking changes

- Lovelace cards pointing to `/local/frame_art/personal/` (or similar without the entry_id) need to be updated. See above.

## Bug fixes carried forward from 6.13.x

- Fix issue #12 (excprocess): Art WebSocket would stay stuck on a dead transport after TV standby until manual reload (6.13.2).
- Fix issue #13 (azebro): repeated "Allow device" prompts on Frame 2024 firmware. Token is now sent on all WS channels (6.13.4).
- REST URL port is no longer hard-coded.

## Beta status

7.0.0b1 is a beta release. The multi-Frame thumbnail path migration runs only once and is irreversible. If you want to roll back, you'll need to manually move files from `www/frame_art/{entry_id}/` back to `www/frame_art/` before reinstalling an older version.
