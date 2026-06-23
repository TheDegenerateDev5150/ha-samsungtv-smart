# Release notes — 8.1.0 (since 8.0.0)

> **Status: pre-release (beta).** 8.1.0 builds on the stable 8.0.0 three-channel
> rework with IP Control reliability and observability improvements.

---

## IP Control

- **Daily device-info refresh**: TV model and firmware version (learned via
  IP Control's `getDeviceInformation`) are now refreshed automatically every
  24h instead of only once at pairing time, so an OTA firmware upgrade is
  picked up without requiring a manual reconfigure.
- **REST port self-heal**: the REST client now honors the configured port and
  falls back between **8001 and 8002 at runtime** on a connection failure,
  persisting the working port — the same self-heal already in place for the
  Art channel (8.0.0) now also covers the REST/device-info path.
- **Read-only state sensors** (`getTVStates` / `getVideoStates`): 12 new
  diagnostic sensors expose the TV's current input source, picture mode, sound
  mode, picture size, speaker select, mute and volume, plus the picture levels
  (contrast, brightness, sharpness, color, tint). They are read-only — these
  values are not settable over IP Control on consumer Frames — and share a
  single coordinator (two JSON-RPC calls per poll for all 12). Gated behind IP
  Control being paired and enabled; paused while the TV is off.
- **Mute and relative volume via IP Control**: `async_mute_volume`,
  `async_volume_up` and `async_volume_down` now try IP Control's
  `muteControl` / `volumeUpDnControl` first (when paired and enabled) and
  fall back to the WebSocket `KEY_MUTE`/`KEY_VOLUP`/`KEY_VOLDOWN` remote keys
  on any IP Control error. `volumeUpDnControl` is relative-only on Frame
  2024/2025 (no absolute level over IP Control — `directVolumeControl` is not
  implemented on consumer Frames), matching the WS keys it replaces.
- **Power-off false-positive fix** (Art Mode / Power switches stuck "on"): when
  IP Control is paired and enabled, a **safe power-only guard** now reads
  `powerControl` on every refresh — even when the *Enable IP Control Art Mode*
  option is off (the default). If the TV reports `powerOff`, `art_mode_status`
  is forced off, overriding a frozen Art-channel WebSocket that kept reporting
  `art='on'` after the TV was switched off. This never calls the firmware-risky
  `artModeControl` method, so it is safe regardless of the Art Mode option.

## Art Mode switch — slow refresh after toggle fix

- **Switch no longer snaps back ~25s after toggling Art Mode**: the IP Control
  `artModeControl` command itself is fast (~100ms), but right after an explicit
  toggle the switch called its own `async_update()`, which read the
  media_player's `art_mode_status` *before* it had caught up (5s poll + Art
  WebSocket propagation, observed up to ~40s on a 2024 Frame). That stale
  pre-toggle value overwrote the fresh optimistic state, so the switch flipped
  back and only recovered on the next media_player cycle. The post-toggle
  self-refresh is removed and an **optimistic-hold guard** now keeps the value
  you just set for up to 45s, ignoring only *contradicting* stale readings — a
  matching reading clears the hold immediately. Applies to both the switch's own
  poll and the media_player state-change listener.

## Art Mode status — accuracy fixes

- **Switches now use the authoritative Art Mode logic**: the `art_mode_status`
  attribute (read by the Power and Frame Art switches) previously re-implemented
  a reduced version of the detection that **ignored the IP Control cache and
  the SmartThings power signal** — so a stale Art-channel WebSocket could pin
  both switches "on" after the TV was powered off. It now delegates to the same
  single source of truth as the media title and the `is_on` property.
- **SmartThings cloud power-off fallback** (for TVs without IP Control): when
  SmartThings reports the TV switched off, `art_mode_status` is forced off. The
  Frame's `switch` capability reports `on` while displaying art and `off` only
  when truly powered off, so this safely overrides a frozen art WebSocket.
  (SmartThings lags ~30-45s, so it is best-effort; IP Control remains the
  instant, authoritative path.)

## Legacy remote WebSocket — automatic 8001 → 8002 port self-heal

- **TokenAuth TVs stuck on the unencrypted 8001 channel now recover on their
  own**: a Frame configured (often historically) on port 8001 rejects every
  remote-control connect with `ms.channel.unauthorized` **and never shows the
  on-screen authorization prompt** — because the prompt + token flow only
  exists on the secure `wss://…:8002` channel. The integration would just keep
  retrying 8001 forever and pause with a "local connection not authorized"
  notification that re-pairing/restarting couldn't fix (the SmartThings/OAuth
  re-auth is unrelated to this local channel). Now, right before pausing
  reconnection, the remote channel **flips 8001 → 8002 once** and retries there
  (SSL + token), and persists the working port to the config entry. On a
  genuine 2024 model whose 8002 is firmware-filtered, the 8002 attempt simply
  fails and the existing guard trips one flip later — no port ping-pong.

## Stale "connection not authorized" notification fix

- **Notifications are now dismissed on setup/reload**: the "Samsung TV — local
  connection not authorized" and IP Control token-problem persistent
  notifications were previously cleared *only* by a clean WebSocket
  reconnect (or a successful IP Control call). If the TV stayed offline or
  unreachable after the guard tripped, neither re-pairing nor a Home
  Assistant restart could ever produce that one clean event, so the
  notification stayed stuck forever even after the underlying problem was
  fixed. Both notifications are now also proactively dismissed every time
  the config entry is set up (covers HA restart, integration reload, and
  Reconfigure → Authentication/IP Control, which all reload the entry) —
  they are safely re-created if the rejection genuinely still occurs.

## Legacy remote WebSocket — unauthorized reconnect loop fix

- **`ms.channel.unauthorized` now trips the auth-blocked guard**: the legacy
  remote-control WebSocket already paused reconnection after 5 consecutive
  rejected tokens (`ms.channel.connect` with a changed token, or `ms.error`
  "No Authorized") to avoid hammering the TV and re-arming the on-screen
  pairing prompt forever. The bare `ms.channel.unauthorized` event some
  firmwares send instead was never handled, so on those TVs the reconnect
  loop ran unthrottled (observed once a second, indefinitely) and every
  remote command sent over that channel failed silently. It now feeds the
  same guard as the other two rejection paths.

## Home Assistant compatibility — config-entry reload deprecation

- **No more "has an update listener and should use it for scheduling a reload"
  warning**: HA deprecated (2026.6, hard error in 2026.12) combining a config
  entry update listener with reload methods called *inside* the config flow.
  The integration did both. Reloads are now scheduled exclusively from the
  update listener: it still applies most option changes live (scan interval,
  app/source lists) via the dispatcher signal — no full reload — and schedules
  a reload only when connection/auth **data** (host, port, token, API key) or a
  structural option (IP Control enable / Art Mode) actually changes. The
  in-flow `async_reload` / `async_update_reload_and_abort` calls were replaced
  accordingly (`async_update_and_abort`, `reload_on_update=False`).

## Art channel WebSocket — zombie-socket recovery

- **Heartbeat / dead-connection detection**: the Art-channel WebSocket now opens
  with an aiohttp `heartbeat` (20s). aiohttp sends periodic PINGs and tears the
  socket down when no PONG comes back, so a "zombie" connection — one the TV
  dropped without a clean TCP close (e.g. an abrupt power-off) — is now detected
  and recycled automatically instead of staying half-open forever. Previously
  such a socket only reconnected on the next user-triggered art request.
- **Stale `art_mode` invalidation on disconnect**: when the receive loop exits
  unexpectedly, the cached `art_mode` is reset to `None` (instead of keeping its
  last, usually `"on"`, value). `art_mode_status` then falls through to the
  independent power sources (IP Control / SmartThings / REST PowerState) while
  the channel is down, and the real value is restored from the first event after
  reconnect. This is the root-cause fix behind the power-off false positive the
  power-only guards already mitigate.

## Reliability & observability

- **Per-TV "slow update" warning**: when a poll cycle takes longer than the
  5s scan interval, the integration now logs its own host-tagged warning
  (`[192.168.x.y] Update took X.Xs, longer than the Xs scan interval`)
  instead of relying solely on Home Assistant's core scheduler warning, which
  cannot identify which TV/entity is responsible in a multi-TV setup.

---

## Known limitations / not yet validated

- Carries forward all 8.0.0 known limitations (see `RELEASE_NOTES_8.0.0.md`),
  including the *Enable IP Control Art Mode* firmware-safety warning.

---

*These notes were assembled from the 8.1.0 codebase (`v8.1-dev`, since the
8.0.0 release). If any 8.1.0bNN pre-release change is missing, add it under
the relevant section.*
