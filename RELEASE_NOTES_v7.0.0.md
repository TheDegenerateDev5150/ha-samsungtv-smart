# v7.0.0 — Multi-Frame support, generation-aware slideshow, and resilience fixes

This is the first stable release of the v7 line. It brings proper multi-Frame TV
support, automatic handling of the slideshow API split across Frame TV
generations, and several resilience improvements.

> ⚠️ **This release contains breaking changes to the thumbnail folder layout.**
> If you reference `/config/www/frame_art/` or `/local/frame_art/` anywhere in
> your configuration (Lovelace cards, `local_file` cameras, `folder` sensors),
> read the **Breaking changes** section below before upgrading.

---

## Highlights

- **Multi-Frame TV support.** Each Frame TV now writes its thumbnails to a
  per-TV subdirectory keyed by config-entry ID, so setups with more than one
  Frame no longer overwrite each other's `current.jpg`. Each TV also gets three
  auto-created folder sensors (`sensor.<tv>_personal` / `_store` / `_other`)
  that track thumbnail folder size and expose a `file_list` attribute for
  gallery cards — no manual `folder` sensor needed.
- **Generation-aware slideshow / auto-rotation.** Samsung split the Frame
  slideshow API across firmware generations. The integration now detects which
  API each TV speaks and routes to it automatically — older Frames (≈2020–2021)
  that only answer `auto_rotation_status` now work, alongside newer Frames
  (2024+) that use `slideshow_status`. Resolves **#18**.
- **Reduced WebSocket traffic.** The expensive `get_content_list` call is now
  throttled to a configurable interval (default 5 minutes, was 15 seconds).
- **Persistent capability detection.** Brightness and colour-temperature support
  is learned once and remembered across restarts, removing the per-startup probe
  delay on TVs (like Frame 2024) that don't implement the dedicated requests.
- **Repairs alert on authentication failure.** When the SmartThings OAuth token
  can no longer be refreshed, a translatable issue is raised in
  **Settings → Repairs** explaining what happened and how to fix it.
- **Thumbnail fallback.** When a live thumbnail fetch fails, the integration now
  reuses a previously-downloaded copy instead of showing an error placeholder.

---

## Generation-aware slideshow (resolves #18)

Samsung Frame TVs do not all speak the same slideshow API:

| Generation (model suffix) | Slideshow API |
|---|---|
| 2024 and newer (`…LS03D…` and later) | `slideshow_status` |
| ≈2020–2021 (`…LS03T…`, `…LS03A…`) | `auto_rotation_status` |

The integration now probes the TV once, records which API it answers in the
config entry, and routes every read and write to that API. The two services
`art_set_slideshow` and `art_set_auto_rotation` are functional **aliases** — both
target the TV's artwork-rotation feature and are routed to whichever underlying
API the TV actually responds to, so you can use either one regardless of model.

The duration field also accepts **custom values** now: in addition to the
presets (`3min`, `15min`, `1h`, `12h`, `1d`, `7d`), you can pass any integer
number of minutes (e.g. `30`, `45`, `180`). Note that some Frame models reject
durations outside a supported set; if a TV refuses a value, it is logged rather
than silently ignored.

*Special thanks to **@prestonmcafee** for the methodical multi-generation
testing (2020 / 2021 / 2024 Frames) that made this diagnosis possible.*

---

## Breaking changes

### Thumbnail folder layout changed from flat to per-TV

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
entity, which now exposes two attributes:

- `entry_id` — the unique identifier for this TV
- `thumbnail_folder` — the full `/local/...` path for use in Lovelace

Anything in your configuration that references the old flat path must be updated
to include the per-TV `entry_id`:

- **Lovelace gallery cards** — `folder: /local/frame_art/YOUR_ENTRY_ID/personal`
- **`local_file` cameras** — `file_path: /config/www/frame_art/YOUR_ENTRY_ID/current.jpg`
- **`folder` sensors** — `folder: /config/www/frame_art/YOUR_ENTRY_ID`

If you had the old path in `homeassistant.allowlist_external_dirs`, allowlist the
new one too.

### Automatic migration (single-Frame installs)

On first start, v7 migrates a single-Frame install automatically: the existing
`current.jpg`, the `personal/` `store/` `other/` directories, and any placeholder
markers are moved into the new `{entry_id}/` subdirectory. This runs once;
subsequent starts are no-ops. If migration fails (permissions, etc.), a `WARNING`
is logged and files are left in place for you to move manually.

If you already have **multiple** Frame TVs configured, only the first config
entry receives the migrated files; the others start with empty per-TV
directories that fill in as artworks change on each TV.

---

## New advanced option

- **Frame Art: content list refresh interval (seconds)** — default `300` (5 min),
  range `30`–`3600`. Lower values keep the gallery counter fresher at the cost of
  more WebSocket traffic; higher values reduce TV load. The Frame Art sensor still
  refreshes every 15 seconds for cheap state (current artwork, slideshow status,
  art mode); only the full content-list scan is throttled to this longer cycle.

---

## Other improvements

- **OAuth failure now surfaces in Repairs.** A translatable issue
  (`oauth_auth_failed`) is created when the SmartThings token can't be refreshed
  and is cleared automatically once a refresh succeeds. Available in 6 languages
  (en, fr, es, it, hu, pt-BR).
- **Thumbnail fallback** (contributed by **@prestonmcafee**): if a live fetch
  fails after retries, a previously-downloaded copy of the same artwork is
  promoted to `current.jpg` instead of an error placeholder.
- **Art Mode state accuracy.** The reported `art_mode_status` now prefers the
  live async Art API value over the WebSocket status flag, which can freeze after
  the art thread is disabled — so the attribute stays correct after standby.

## Bug fixes carried forward from 6.13.x

- **#12** (excprocess): Art WebSocket could stay stuck on a dead transport after
  TV standby until a manual reload (6.13.2).
- **#13** (azebro): repeated "Allow device" prompts on Frame 2024 firmware; the
  token is now sent on all WebSocket channels (6.13.4).
- REST URL port is no longer hard-coded.

---

## Upgrade notes

1. Back up your `www/frame_art/` directory if you have a custom setup.
2. Update via HACS, then restart Home Assistant.
3. Update any Lovelace cards, `local_file` cameras, and `folder` sensors to the
   per-TV path (see **Breaking changes**).
4. If you use SmartThings OAuth and later see a **Repairs** alert about
   authentication, reconfigure the integration to re-authenticate.

Rolling back requires manually moving files from `www/frame_art/{entry_id}/`
back to `www/frame_art/` before reinstalling a 6.x release.

---

## Acknowledgements

Special thanks to **@prestonmcafee**, whose detailed, multi-generation testing
drove much of this release. Running 2020, 2021, and 2024 Frame TVs side by side,
he supplied per-model state dumps, firmware versions, and methodical before/after
logs that pinpointed two issues no single-TV setup would have surfaced:

- the slideshow API split between `slideshow_status` (newer Frames) and
  `auto_rotation_status` (older Frames), which is the basis of the
  generation-aware routing (#18); and
- the `art_mode_changed`-without-request-id confirmation on older Frames, which
  is what the Art Mode activation fix relies on.

He also suggested the cached-thumbnail fallback for `current.jpg`. Older Frame
owners benefit directly from his work.
