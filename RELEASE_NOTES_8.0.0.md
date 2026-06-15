# Release notes — 8.0.0 (since 7.1.x)

> **Status: beta.** 8.0.0 is a major rework of the SmartThings/Frame handling.
> It is distributed as `8.0.0bNN` pre-releases until validated on more TV
> generations. Back up your config before upgrading from the 7.1.x line.

8.0.0 turns the Frame integration into a **three-channel** design — SmartThings
(cloud), the local WebSocket, and the new **IP Control** channel (JSON-RPC) —
with each channel independently selectable and resilient to a bad credential.

> [!WARNING]
> **Do not enable *Enable IP Control Art Mode*** unless you know your firmware
> handles it correctly. On affected firmwares it can leave **Art Mode completely
> broken** — detection stuck/flickering, switching unreliable — and the damage
> can persist at the TV level, requiring a **factory reset** to recover. This was
> observed on a **QE55LS03D with firmware 2123**. The option is **off by
> default**; leave it off and let Art Mode run over the WebSocket / Frame Art
> channel (unaffected). Power on/off over IP Control is a separate setting and is
> **not** impacted. See *Troubleshooting → "IP Control reports Art Mode 'on' when
> it isn't"* in the README.

---

## Highlights

- **Native SmartThings OAuth2** authentication (in addition to Personal Access
  Token), using Home Assistant's built-in OAuth flow.
- **Multi-Frame support**: multiple Frame TVs run side by side, each isolated by
  config-entry id (tokens, art folders, state — no cross-talk).
- **New IP Control channel** (JSON-RPC, port 1516): a SmartThings-free path for
  power, reboot and Art Mode, independent of the WebSocket channels.
- **Token resilience** across all three authentication methods: clear, self-
  clearing notifications and automatic back-off instead of silent failure loops.
- **Reboot button** for Frames paired with IP Control.
- **Full localization**: all UI strings complete in 6 languages.

---

## SmartThings authentication

- Added **OAuth2** as the recommended authentication method, alongside the
  existing **Personal Access Token (PAT)**. The auth method is chosen in the
  config flow and shown as the current method when reconfiguring.
- SmartThings credential failures now surface through Home Assistant's native
  **Repairs** issue (auto-cleared on a successful token refresh) rather than
  failing silently.

## IP Control (new channel — JSON-RPC, port 1516)

- **Pairing** from the integration options (TV must be ON and in normal
  viewing, not Art Mode). The access token is stored per entry and **survives
  TV reboots** (no re-pairing needed afterwards).
- **Power on/off** and **reboot** over a channel that is independent of the
  WebSocket — so it still works when the Art WebSocket has gone unresponsive.
- **Authoritative Art Mode read**, power-state-gated: a TV in standby reports
  Art Mode *off* even though the firmware's art-mode getter still returns the
  last value (fixes switches showing **on** after a Home Assistant restart with
  the TV off).
- **Art Mode set** now goes through IP Control **first**, falling back to the
  WebSocket only on failure — avoiding the WebSocket path that could become
  unresponsive.
- **Enable/disable toggle** in the options: turn the whole IP Control channel
  off without un-pairing (hides the reboot button and stops IP Control polling).
- **Power-on method**: "IP Control" can be selected as the power-on method,
  available even without SmartThings, with WOL as automatic fallback.
- Robust error handling: the firmware's flat `-32700` "Parse error" (returned
  for a stale/invalid token) is detected and treated as an auth error instead
  of being swallowed.

## New entities

- **Reboot button** (`button`): reboots the TV via IP Control. Created only when
  IP Control is paired and enabled; powers the TV on first if it is off.

## Token resilience & notifications

- **Local WebSocket (PAT)**: the stored token is validated as a string before
  use (a token polluted with OAuth data no longer corrupts the connection URL).
  Repeated token rejections (`No Authorized` / a storm of new tokens) now pause
  reconnection instead of endlessly re-triggering the on-screen authorization
  prompt, and raise a clear notification. The notification clears automatically
  once the connection is authorized again.
- **IP Control**: a rejected token raises a "re-pair required" notification and
  pauses IP Control features; it clears automatically on the next success.
- **SmartThings**: native Repairs issue (see above).

## Frame / Art Mode

- Art Mode switch with retry and live state. By default it tracks Art Mode over
  the WebSocket / Frame Art channel; IP Control read/switch is opt-in (see the
  warning above).
- **Responsive switch sync**: the Art Mode and power switches poll every 5 s
  (matching the SmartThings cadence) instead of Home Assistant's 30 s default,
  and `art_mode_status` is now published **immediately** on an art-channel
  transition (`art_mode_changed` / `go_to_standby`) instead of waiting for the
  next poll — the switch reflects a toggle within ~1 s.
- The displayed artwork is surfaced as the media-player image (with cache
  busting so the frontend reloads it when the picture changes), and the running
  app `art` is shown as an **"Art Mode"** title.
- Slideshow control routed automatically to the API the TV actually supports
  (`slideshow` vs `auto_rotation`), accepting custom durations.
- Bundled `folder-gallery-card` for the art gallery frontend.

## Localization

- All UI strings (config, options, IP Control pairing, the new toggle and the
  reboot button) are complete in **English, French, Spanish, Italian,
  Portuguese (BR) and Hungarian**. Several Spanish/Italian/Portuguese/Hungarian
  keys that were missing in the 7.1.x line have been filled in.

---

## Known limitations / not yet validated

- IP Control **power/reboot** is confirmed on **Frame 2024/2025**. Older
  generations (Tizen 5.5 / 6.0) are **not yet validated** — protocol differences
  possible.
- IP Control **Art Mode** (the *Enable IP Control Art Mode* option) is **not
  safe on all firmwares**: it can wedge or break Art Mode entirely and may need
  a factory reset to recover (seen on QE55LS03D fw 2123). It stays **off by
  default** — see the warning above.
- The reboot/IP-Control recovery of an unresponsive ("zombie") Art WebSocket is
  implemented but **not yet confirmed empirically** in that exact state.
- Brightness / colour-temperature capability flags are re-detected on every
  start (not yet persisted).
- The three power-on-method labels are currently English-only in all locales.

---

*These notes were assembled from the 8.0.0 codebase. If any 7.1.x point-release
change is missing, add it under the relevant section.*
