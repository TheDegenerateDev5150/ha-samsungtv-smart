# v7.1.0 — Frame TV power/Art Mode docs, multi-frame gallery upload, timezone-aware datetimes

This is the second stable release of the v7 line. It builds directly on v7.0.0
(multi-Frame support, generation-aware slideshow) and focuses on Art Mode / power
state accuracy on Frame TVs, a refreshed bundled gallery card, and clearer
documentation of how power control behaves on Frame TVs.

> ⚠️ **If you are upgrading from a 6.x release, the v7.0.0 breaking change to the
> thumbnail folder layout still applies.** See the **Breaking changes** section
> further down before upgrading. Upgrading from v7.0.0 → v7.1.0 requires no
> configuration changes.

---

## New in 7.1.0

- **Timezone-aware datetime handling in `media_player.py`.** Internal time
  bookkeeping now uses Home Assistant's `dt_util` for UTC time and timezone-aware
  datetime objects throughout, replacing naive `datetime.utcnow()` usage. This
  aligns with Home Assistant's move away from naive datetimes and removes the
  associated deprecation warnings.

- **Multi-frame upload routing in the bundled gallery card (v1.3.0).** When a
  gallery points at a folder of local photos (i.e. not a TV `store`/`personal`
  folder, and the image isn't already a `SAM-`/`MY_` artwork) and you trigger an
  upload from the lightbox, the card now detects how many Frame TVs are present.
  With more than one Frame, it shows an *"Upload to which Frame?"* chooser
  offering each Frame by name plus an **All Frames** option that uploads to every
  Frame in turn. With a single Frame, the upload goes straight through, unchanged.
  Frame discovery uses the `media_player` `art_mode_status` attribute, so it picks
  up every Frame the integration manages with no extra configuration — and builds
  directly on the Art Mode state-accuracy fix from v7.0.0, which keeps that
  attribute present and correct. The card is registered automatically on Home
  Assistant start as before; no manual installation needed.

- **Documented power control on Frame TVs.** The README now explains the
  three-state nature of a Frame TV (Off → Art Mode → On), why Art Mode is a
  powered-on state, and why a reliable power-off requires SmartThings. See the
  notes below and the new *Power control on Frame TVs* section in the README.

### A note on Frame TV power control

A Frame TV cannot be in Art Mode and powered off at the same time — Art Mode is a
powered-on state where the panel displays artwork. This is a Samsung hardware
design, not an integration limitation. Consequently:

- **With SmartThings configured**, the Power switch (`switch.<tv>_power`) issues a
  hardware-level off command that works from any state, including Art Mode. This
  is the recommended setup for Frame TVs.
- **Without SmartThings**, the integration can only fall back to WebSocket
  control, and Frame TVs expose no true "power off" over WebSocket — the available
  `KEY_POWER` command merely toggles between normal viewing and Art Mode. The
  Power switch will therefore appear to cycle between modes rather than fully
  powering the TV off.

Use the dedicated `switch.<tv>_power` entity rather than the power button on the
standard media player card, which sends a raw `KEY_POWER` toggle with no
Frame-aware logic. The JSON-RPC IP-control `powerControl` endpoint is being
evaluated as a possible future path for explicit power-off without SmartThings.

---

## Carried over from v7.0.0

The following sections describe the v7.0.0 feature set, which v7.1.0 includes in
full. They are repeated here so this document stands alone for anyone upgrading
directly from a 6.x release.

### Highlights

- **Multi-Frame TV support.** Each Frame TV writes its thumbnails to a per-TV
  subdirectory keyed by config-entry ID, so setups with more than one Frame no
  longer overwrite each other's `current.jpg`. Each TV also gets three
  auto-created folder sensors (`sensor.<tv>_personal` / `_store` / `_other`)
  that track thumbnail folder size and expose a `file_list` attribute for
  gallery cards — no manual `folder` sensor needed.
- **Generation-aware slideshow / auto-rotation.** Samsung split the Frame
  slideshow API across firmware generations. The integration detects which API
  each TV speaks and routes to it automatically — older Frames (≈2020–2021) that
  only answer `auto_rotation_status` now work, alongside newer Frames (2024+)
  that use `slideshow_status`. Resolves **#18**.
- **Reduced WebSocket traffic.** The expensive `get_content_list` call is
  throttled to a configurable interval (default 5 minutes, was 15 seconds).
- **Persistent capability detection.** Brightness and colour-temperature support
  is learned once and remembered across restarts, removing the per-startup probe
  delay on TVs (like Frame 2024) that don't implement the dedicated requests.
- **Repairs alert on authentication failure.** When the SmartThings OAuth token
  can no longer be refreshed, a translatable issue is raised in
  **Settings → Repairs** explaining what happened and how to fix it.
- **Thumbnail fallback.** When a live thumbnail fetch fails, the integration
  reuses a previously-downloaded copy instead of showing an error placeholder.

### Generation-aware slideshow (resolves #18)

Samsung Frame TVs do not all speak the same slideshow API:

| Generation (model suffix) | Slideshow API |
|---|---|
| 2024 and newer (`…LS03D…` and later) | `slideshow_status` |
| ≈2020–2021 (`…LS03T…`, `…LS03A…`) | `auto_rotation_status` |

The integration probes the TV once, records which API it answers in the config
entry, and routes every read and write to that API. The two services
`art_set_slideshow` and `art_set_auto_rotation` are functional **aliases** — both
target the TV's artwork-rotation feature and are routed to whichever underlying
API the TV actually responds to, so you can use either one regardless of model.

The duration field also accepts **custom values**: in addition to the presets
(`3min`, `15min`, `1h`, `12h`, `1d`, `7d`), you can pass any integer number of
minutes (e.g. `30`, `45`, `180`). Some Frame models reject durations outside a
supported set; if a TV refuses a value, it is logged rather than silently ignored.

### Breaking changes

#### Thumbnail folder layout changed from flat to per-TV

**Before (v6.x):**
```
www/frame_art/
  current.jpg
  personal/  store/  other/
```

**v7:**
```
www/frame_art/
  {entry_id}/
    current.jpg
    personal/  store/  other/
```

`{entry_id}` is the 32-character hex identifier of the TV's config entry. Find
yours in **Developer Tools → States** on the `sensor.<tv_name>_frame_art`
entity, which exposes two attributes:

- `entry_id` — the unique identifier for this TV
- `thumbnail_folder` — the full `/local/...` path for use in Lovelace

Anything in your configuration that references the old flat path must be updated
to include the per-TV `entry_id`:

- **Lovelace gallery cards** — `folder: /local/frame_art/YOUR_ENTRY_ID/personal`
- **`local_file` cameras** — `file_path: /config/www/frame_art/YOUR_ENTRY_ID/current.jpg`
- **`folder` sensors** — `folder: /config/www/frame_art/YOUR_ENTRY_ID`

If you had the old path in `homeassistant.allowlist_external_dirs`, allowlist the
new one too.

#### Automatic migration (single-Frame installs)

On first start, v7 migrates a single-Frame install automatically: the existing
`current.jpg`, the `personal/` `store/` `other/` directories, and any placeholder
markers are moved into the new `{entry_id}/` subdirectory. This runs once;
subsequent starts are no-ops. If migration fails (permissions, etc.), a `WARNING`
is logged and files are left in place for you to move manually.

If you already have **multiple** Frame TVs configured, only the first config
entry receives the migrated files; the others start with empty per-TV
directories that fill in as artworks change on each TV.

### New advanced option

- **Frame Art: content list refresh interval (seconds)** — default `300` (5 min),
  range `30`–`3600`. Lower values keep the gallery counter fresher at the cost of
  more WebSocket traffic; higher values reduce TV load. The Frame Art sensor still
  refreshes every 15 seconds for cheap state (current artwork, slideshow status,
  art mode); only the full content-list scan is throttled to this longer cycle.

### Other improvements

- **OAuth failure now surfaces in Repairs.** A translatable issue
  (`oauth_auth_failed`) is created when the SmartThings token can't be refreshed
  and is cleared automatically once a refresh succeeds. Available in 6 languages
  (en, fr, es, it, hu, pt-BR).
- **Thumbnail fallback** (contributed by **@prestonmcafee**): if a live fetch
  fails after retries, a previously-downloaded copy of the same artwork is
  promoted to `current.jpg` instead of an error placeholder.
- **Art Mode state accuracy.** The reported `art_mode_status` prefers the live
  async Art API value over the WebSocket status flag, which can freeze after the
  art thread is disabled — so the attribute stays correct after standby. This
  also keeps the Art Mode and Power switches in sync on Frame TVs (including the
  Frame 2025). Resolves the state-reporting part of **#17**.

### Bug fixes carried forward from 6.13.x

- **#12** (excprocess): Art WebSocket could stay stuck on a dead transport after
  TV standby until a manual reload (6.13.2).
- **#13** (azebro): repeated "Allow device" prompts on Frame 2024 firmware; the
  token is now sent on all WebSocket channels (6.13.4).
- REST URL port is no longer hard-coded.

---

## Upgrade notes

1. Update via HACS, then restart Home Assistant.
2. **Upgrading from v7.0.0 → v7.1.0**: no configuration changes are required.
3. **Upgrading from 6.x**: back up your `www/frame_art/` directory if you have a
   custom setup, then update any Lovelace cards, `local_file` cameras, and
   `folder` sensors to the per-TV path (see **Breaking changes**).
4. If you use SmartThings OAuth and later see a **Repairs** alert about
   authentication, reconfigure the integration to re-authenticate.
5. For reliable power-off on a Frame TV, configure SmartThings (OAuth2
   recommended); see *A note on Frame TV power control* above.

Rolling back to a 6.x release requires manually moving files from
`www/frame_art/{entry_id}/` back to `www/frame_art/` before reinstalling.

---

## Acknowledgements

Special thanks to **@prestonmcafee**, whose detailed, multi-generation testing
drove much of the v7.0.0 work — running 2020, 2021, and 2024 Frame TVs side by
side to pinpoint the slideshow API split (#18) and the `art_mode_changed`
confirmation behaviour on older Frames, and suggesting the cached-thumbnail
fallback for `current.jpg`.
