# Release notes — 8.1.0 (since 8.0.0)

## Art Mode — faster switch/media_player updates when toggling Art Mode

- **`art_set_artmode`/the Art Mode switch could take up to 5s to confirm a
  change**: some Frames (e.g. 2020/2021) never echo a matching response to
  `set_artmode_status` — only an `art_mode_changed` broadcast confirms the
  change, and that broadcast carries no request id, so it couldn't be matched
  to the pending request and the call always waited out the full 5s timeout
  before falling back to checking the broadcast-updated state. The wait now
  races the direct response against that broadcast and returns as soon as
  either confirms the requested state, instead of always paying the full
  timeout.

## Remote entity — fix regression where Home/Source/Power/Menu stopped working

- **Remote entity silently stopped being (re)created after a restart**: 8.1.0b15
  added a guard against a duplicate `remote.<tv>` entity (caused by a rapid
  reload firing a stale 5s-delayed setup callback on top of the new one) by
  checking the **entity registry** for an existing `remote` entry before
  creating one. That check was wrong: the entity registry persists across full
  Home Assistant restarts, so on the very first normal restart after updating,
  it always found the previous session's registry entry and bailed out —
  meaning the remote entity was never actually added again, for any TV, until
  the integration happened to reload in a way that cleared it. This is what
  broke the Home/Source/Power/Menu/d-pad commands (which go through the
  `remote.<tv>` entity) starting at 8.1.0b15. Fixed by properly cancelling the
  pending 5s callback on unload (`entry.async_on_unload`) instead of probing
  the persistent registry — the original duplicate-add race is still
  prevented, but normal restarts now recreate the remote entity correctly
  every time.

> **Status: pre-release (beta).** 8.1.0 builds on the stable 8.0.0 three-channel
> rework with IP Control reliability and observability improvements.

---

## IP Control

- **No more `ERROR ... TV is powered off` log noise from the state sensors**:
  the read-only IP Control state coordinator (`getTVStates`/`getVideoStates`)
  already skipped polling while the TV is off, but it did so by raising
  `UpdateFailed("TV is powered off")`. Home Assistant logs the first failure of
  each streak at `ERROR`, so every off→on transition produced a fresh
  `ERROR ... Error fetching IP Control state ... TV is powered off` line. A
  powered-off TV is an expected, recurring condition — not a failure — so the
  coordinator now returns a `powered_off` snapshot instead of raising. The state
  sensors still go *unavailable* while the TV is off (via that flag), but no
  ERROR is logged.
- **REST / WebSocket port no longer fight on split-port TVs (~2020 Frames)**:
  some 2020 Frames serve the REST/HTTP API on **8001** while the secure token
  WebSocket + Art channel live on **8002**. All three channels persisted their
  self-healed port to a single shared config value, so the REST self-heal (which
  learned 8001) and the remote-channel self-heal (which needs 8002) kept
  overwriting each other — on every reload the remote channel re-ran its
  `8001 → 8002` flip and REST re-flipped it back, an endless ping-pong (visible
  as repeated *"switching to the secure 8002 channel"* / *"succeeded on 8001 --
  switching to it"* warnings). REST now learns and persists its **own** port
  (`rest_port`), decoupled from the WS/Art port, so each channel keeps the port
  that works for it. Also fixes a nonsensical *"Art API: Port changed from 8002
  to 8002"* log line.
- **Duplicate `remote.<tv>` entity on rapid reload**: the remote entity is added
  via a 5s-delayed callback that wasn't cancelled on unload, so reloading the
  integration within ~5s fired a stale pending callback on top of the new
  setup's — registering a second remote with the same unique id (*"Platform
  samsungtv_smart does not generate unique IDs ... ignoring remote.<tv>"*). The
  setup now skips adding a remote when one already exists for the entry.
- **Older Frames (~2020) TLS handshake fix (`dh key too small`)**: some 2020
  Frames negotiate a Diffie-Hellman group smaller than 1024 bits on the IP
  Control port (1516), which OpenSSL rejected even after the existing
  `@SECLEVEL=1` retry — so *all* IP Control on those TVs (power, device info,
  art-mode read) failed with `[SSL: DH_KEY_TOO_SMALL]`. The legacy-TLS retry now
  drops to `@SECLEVEL=0`. These are local, self-signed panels already contacted
  with `CERT_NONE`, so this is safe and strictly looser than the previous level.
- **Stop re-querying not-installed apps**: an app present in the configured
  app/source list but not installed on the TV returned `404 Not found` on every
  scan — on TVs that never report an installed-app list (e.g. some 2020 Frames)
  this meant the same missing app was polled forever (1900+ times in one logged
  session). Such app ids are now remembered and skipped until the TV reports a
  fresh installed-app list.

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

## Art Mode — settings entities

- **New "Brightness Sensor" select** (Frame models that report it): the Art Mode
  ambient brightness sensor (on/off) is now exposed as a select alongside the
  existing **Motion Sensitivity** and **Motion Timer** selects, all read/write
  over the Art channel. Created only when the TV reports the setting. This rounds
  out the Art Mode settings the TV exposes via `get_artmode_settings`
  (`brightness`, `color_temperature`, `motion_sensitivity`, `motion_timer`,
  `brightness_sensor_setting`). Note: the Frame's general *Sleep Timer*
  (System → Time, disabled in Art Mode) is **not** exposed by any channel — the
  motion-based auto-off in Art Mode is the **Motion Timer** select.
- **Clearer log when a model has no motion/brightness sensor**: when the TV
  reports none of `motion_sensitivity` / `motion_timer` /
  `brightness_sensor_setting`, the integration now logs this at `INFO` (instead
  of `debug`), stating explicitly that those three controls are intentionally
  not created because the model has no such sensor. Expected on Frames without
  the motion/ambient-light sensor (e.g. some 2020/2021 models) — it is not an
  error.

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
- **Clearer log when a TV has no working secure 8002 channel**: when the remote
  channel has already flipped 8001 → 8002 and the secure channel *also* keeps
  rejecting, the integration now says so explicitly instead of logging a
  generic "re-pair required". Per the decompiled TV server
  (`notes/QN55LS03FAFXZA/PORTS.md`), some firmwares fail to bring up the 8002
  TLS vhost at all (`can't create vhost for '8002' port`, observed on some 2020
  Frames), so neither 8001 nor 8002 can complete the token handshake — and a
  re-pair can't fix what is a TV-side limitation. The new message names that
  case directly to save debugging time.

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

## Art Mode — thumbnails for Art Store content

- **Stop hammering uncached Art Store (SAM-S\*) thumbnails**: the Frame only
  keeps a thumbnail in its local cache once the content has actually been
  materialized (displayed, favorited, downloaded). For Art Store items that
  aren't cached yet, `get_thumbnail` returns `SYSTEM_FAIL` / 0 bytes because
  there is genuinely nothing to serve — a structural condition, not a transient
  transport error. The integration previously treated it as transient: 3
  retries, an error placeholder, and a 5-minute global backoff, repeated every
  poll, spamming the log for content that could never resolve until the TV
  cached it. Art Store content is now fetched on a single attempt and, on
  failure, left quietly (no placeholder, no backoff) with a calm debug line.
  Personal photos (MY_F\*) keep the multi-attempt retry, since their failures
  really are transient.
- **Refresh on new content**: the Art channel now also listens for the TV's
  `image_added` / `image_of_list_added` broadcasts (it already handled
  `image_selected`, `favorite_changed`, etc.). These fire when the TV
  materializes new content locally — exactly when a previously-uncached Art
  Store thumbnail becomes fetchable — so the skipped thumbnail is retried as
  soon as it can actually succeed, instead of waiting for the next poll.
- **Art Store thumbnail no longer takes minutes to appear**: two fixes that
  together caused a freshly favorited/displayed Art Store image to keep showing
  the *previous* artwork's thumbnail for several minutes (until the displayed
  artwork happened to change). First, the "do we already have this thumbnail?"
  check is now **content-aware** — a leftover `current.jpg` from an earlier
  artwork no longer masquerades as the current content's thumbnail and
  suppresses the fetch. Second, favoriting Art Store content does **not** emit
  an `image_added` broadcast (only personal uploads do), so relying on that
  event alone meant the retry never fired; the integration now arms a short
  retry cooldown after an uncached Art Store miss and picks the thumbnail up
  within ~30s of the TV caching it, without re-fetching on every poll.
- **No more flashing the wrong artwork during matte/select operations**: the
  Frame occasionally returns a spurious one-off `content_id` from
  `get_current_artwork` during matte changes (observed: a single poll reporting
  an unrelated id such as `SAM-F0222` while another artwork is actually on
  screen, corrected on the very next poll). The integration used to expose that
  reading immediately — briefly showing the wrong artwork in HA and triggering a
  wasted thumbnail fetch. A changed `content_id` is now **debounced**: it must be
  seen on two consecutive polls before it is exposed, so a single bad reading is
  ignored. Legitimate changes still appear promptly (polls are sub-second to a
  few seconds apart during art activity).

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
- **Art-app error codes are now decoded in the logs**: the Art channel's
  `{"event": "error", "error_code": N}` replies (e.g. on a failed thumbnail
  download) used to log only the bare numeric code, which is meaningless
  without cross-referencing the decompiled firmware notes. Debug logs now show
  the decoded name alongside it (e.g. `SYSTEM_FAIL (-1)`, `NOT_SUPPORTED_API
  (-9)`, `INSUFFICIENT_SPACE (-11)`), making it possible to tell a generic
  TV-side failure apart from e.g. a full thumbnail cache or an unsupported
  request on a given firmware.

---

## Known limitations / not yet validated

- Carries forward all 8.0.0 known limitations (see `RELEASE_NOTES_8.0.0.md`),
  including the *Enable IP Control Art Mode* firmware-safety warning.

---

*These notes were assembled from the 8.1.0 codebase (`v8.1-dev`, since the
8.0.0 release). If any 8.1.0bNN pre-release change is missing, add it under
the relevant section.*
