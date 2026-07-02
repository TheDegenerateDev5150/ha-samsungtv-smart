# Release notes — 8.3.0 (since 8.2.0)

> **Status: pre-release (beta).** 8.3.0 builds on 8.2.0.

## Frame Art — `current.jpg` uses the already-downloaded thumbnail first (8.3.0b5)

- **When the artwork changes, `current.jpg` is now taken from the local copy we
  already downloaded (personal/store/other) *first*, and the TV is only queried
  if we don't have it.** Previously the card did the flaky live TV fetch first
  (which returns `SYSTEM_FAIL` on some Frame models), retried three times over
  ~8 s, and only *then* fell back to the cached copy — so `current.jpg` could
  lag ~30–45 s even for artworks whose thumbnail was already on disk. Downloaded
  thumbnails don't change, so the local copy is both instant and more reliable.
  Genuinely new artwork (no local copy yet) still falls back to a live fetch.

## Frame Art — current artwork updates much faster (8.3.0b4)

- **A manual / gallery art change now shows up in the Frame Art sensor and
  `current.jpg` in ~1–2 s instead of up to ~30 s.** Two things caused the lag:
  the art coordinator polled every 15 s, and a *changed* `content_id` had to be
  seen on **two consecutive polls** before being trusted (a guard against
  spurious one-off readings from the TV) — so a change took up to two full
  intervals to surface.
  - The art coordinator now polls every **5 s** (the cheap `get_current_artwork`
    read; the heavier content-list fetch stays throttled separately).
  - When the change arrives as a **WebSocket art broadcast** (`image_selected`,
    matte/slideshow/favorite/rotation) — which is definitive, not a glitch — the
    new `content_id` is **trusted immediately**, skipping the two-poll
    confirmation. The glitch guard still applies to unsolicited TV-side reads.
  - Note: a slow `current.jpg` can still occur if the TV itself returns
    `SYSTEM_FAIL` on the thumbnail request (a firmware issue); the integration
    retries and falls back to a cached copy.

## Folder Gallery card — fullscreen-preview buttons work again in lightbox mode (8.3.0b3)

- **Fix: the lightbox buttons (Display on TV / Unfavourite / Delete / Upload)
  did nothing** when the single tap was set to *Open preview (lightbox)* in the
  visual editor. That mode cleared the card's `action`, but the buttons rely on
  it for the Frame TV entity and the service to call, so every button silently
  no-op'd. The editor now keeps the gallery type's primary action in lightbox
  mode, and the Frame TV entity is also persisted on its own `frame_tv_entity`
  key so the buttons always resolve a target.
  - After updating, **re-open the card in the visual editor and save once** (or
    re-select the Frame TV entity) so the new `frame_tv_entity` is written.

## Art Mode is detected immediately again after the polling rework (8.3.0b2)

On some models (notably 2024 Frames where IP Control can't report the art
state and the TV's REST `PowerState` stays `on` while displaying art),
entering/leaving **Art Mode** is only learned from SmartThings. After the ST
poll was throttled (below), a `select_image` / Art Mode change could take up to
the ST interval (~30 s) to show up in `art_mode_status` / the current art.
The integration now **forces an immediate SmartThings poll on an art-mode
transition** (the local Art WebSocket already broadcasts it), so Art Mode is
reflected within a second or two again — without giving up the throttle for
idle polling.

## SmartThings polling — local WebSocket first, far fewer cloud calls

Ahead of Samsung's move to a **paid SmartThings API** (free access phasing out
around October 2026), this release reworks polling so the **local WebSocket is
the primary state source** and the SmartThings cloud is a throttled fallback,
cutting cloud API usage dramatically.

- **The local WebSocket / UPnP / IP Control drive power, app, volume and mute**
  (every 5 s, unchanged). SmartThings is now only polled for the data that has
  no local equivalent: channel name, source labels, picture mode, sound mode
  and power/energy metering.
- **SmartThings is throttled.** It is polled at a configurable cadence while the
  TV is **ON** (new advanced option *SmartThings poll interval when on*, default
  **30 s**), and at a fixed **30 s keepalive** otherwise. When the TV powers on,
  one SmartThings poll is forced immediately so the cloud-only fields refresh
  right away instead of lagging by the interval.
- **The five power/energy sensors now share a single poll.** Previously each of
  the five `powerConsumptionReport` sensors independently called
  `get_device_status` on the *same* device every 15 s (20 calls/min of pure
  redundancy). They now read from one shared coordinator that makes a single
  call per cycle and **skips entirely while the TV is off** — while still
  polling when the Frame is displaying **Art** (it keeps drawing power), so
  art-mode consumption stays visible.
- **The picture-mode select and the child light sensors** (illuminance /
  brightness) are now power-gated and throttled to the same cadence, instead of
  polling the cloud every 15–30 s regardless of whether the TV is on.

On a realistic 6 h-on / 18 h-off day this takes a fully-equipped Frame TV from
roughly **53,000 SmartThings calls/day to about 7,500 (~86% fewer)**, with the
largest savings while the TV is off.

### New option

*Configure → advanced options → **SmartThings poll interval when on** (seconds)*
— default `30`, range `5`–`600`. Lower it for snappier channel / picture-mode
updates at higher API cost; raise it to minimise calls. Changing it reloads the
integration. The off-state keepalive is fixed at 30 s.

See [`docs/SmartThings_API_Usage.md`](docs/SmartThings_API_Usage.md) for the full
breakdown of what is polled and why.
