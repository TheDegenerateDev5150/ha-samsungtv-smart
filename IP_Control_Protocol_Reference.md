# Samsung IP Control (JSON-RPC) — Protocol Reference

Consolidated reference for the undocumented JSON-RPC IP Control interface on recent
Samsung TVs, synthesised from three sources:

- **Empirical testing** on a Frame 2024 (`QE55LS03D`) and 2025 (`GQ50LS03F`).
- The **`py-samsungtv`** clean-room library (method/param surface).
- Samsung's official **Wall PRO IP Command List** (API Wall v1.2), which exposes the
  same JSON-RPC method names for LED-wall displays and is the closest thing to a
  vendor-published spec.

This is the working spec for an eventual `api/ipcontrol.py` module.

---

## Transport

- **URL:** `https://<tv_ip>:1516/` — HTTPS, POST, JSON-RPC 2.0 envelope.
- **Port:** `1516` (the library also references `1515`; `1516` is what responds on
  our test TVs). Port opens only when **IP Remote** is enabled on the TV.
- **TLS:** self-signed panel certificate → verification disabled
  (`check_hostname = False`, `verify_mode = CERT_NONE`).
- **Headers:** only `Accept: application/json` and `Content-Type: application/json`
  are required. Note: `py-samsungtv` uses aiohttp and lets it add its default
  `User-Agent`/`Accept-Encoding`, and it still works — so the breaking header the
  reporter saw from Postman was a Postman-specific one, not the standard transport
  headers. Either a header-minimal `http.client` request or an aiohttp request with
  the two headers above is fine.
- **Old-TV TLS fallback:** `py-samsungtv` retries with `DEFAULT:@SECLEVEL=1` ciphers
  on a "dh key too small" SSL error — pre-2016 panels negotiate a weak DH group.
  Relevant when testing older Frames: a plain `curl` may fail the TLS handshake and
  need `--ciphers DEFAULT@SECLEVEL=1`.

### Request envelope

```json
{ "jsonrpc": "2.0", "id": 1, "method": "<method>", "params": { "AccessToken": "...", ... } }
```

- `params` is omitted entirely for `createAccessToken`.
- For every other method the `AccessToken` lives inside `params`.
- `id` may be any value (the library increments it per request; a constant works too).

---

## Authentication flow

1. **Pair** — call `createAccessToken` (no token). The TV shows an on-screen
   authorization prompt and returns `{"result": {"AccessToken": "<token>"}}`.
2. **Use** — pass that token in `params.AccessToken` on every subsequent call.

**Confirmed behaviours (Frame 2024):**

- Pairing **only works when the TV is in normal viewing — NOT Art Mode.** In Art
  Mode the endpoint does not respond and the call times out. This is the #1 pairing
  gotcha.
- The token **persists across power cycles**: `powerOn` succeeds against a fully-off
  TV with a stored token and no new prompt, so we pair once and keep the token.
- **TV setting required:** *Settings → All Settings → Connections → Network →
  Expert Settings → Enable IP Remote*. (Menu path may differ on older firmware.)

---

## Error codes

Returned as `{"error": {"code": <int>, "message": "..."}}`:

| Code | Meaning | Suggested handling |
|---|---|---|
| `-32000` | Unknown error | log, surface generic failure |
| `-32001` | Not supported | method/feature absent on this model → disable that capability |
| `-32002` | Failed | transient failure → retry / fall back |
| `-32003` | Invalid operation | bad state for this command |
| `-32010` | Unauthorized | token invalid/expired → trigger re-pairing |

---

## Methods

`AccessToken` is implied in `params` for all methods except `createAccessToken`.
"Confirmed" = personally verified on the Frame 2024; others are from the library /
Wall PRO spec and need on-device confirmation per model.

| Method | Extra params | Returns | Notes |
|---|---|---|---|
| `createAccessToken` | — | `AccessToken` | Pairing. No token. On-screen prompt. **Confirmed.** |
| `getTVStates` | — | `power`, `inputSource`, `pictureMode`, `soundMode`, `mute`, `artMode`, `pictureSize`, `atvDtv`, `airCable`, `channelNum` | Authoritative state snapshot. High value for the integration. |
| `getVideoStates` | — | `volume`, `contrast`, `brightness`, `sharpness`, `color`, `tint`, `pictureSize`, `soundMode`, `speakerSelect` | Picture/sound levels. |
| `powerControl` | `power` *(optional)* | `power` | No `power` = **read state**; with `power` = set. `power` ∈ `powerOn` / `powerOff` / `reboot`. Read returns `powerOn` in Art Mode. **Confirmed: read, on, off (incl. off from Art Mode).** |
| `remoteKeyControl` | `remoteKey` | — | Full virtual remote (see RemoteKey list). The WS `KEY_*` replacement if 8001/8002 die. |
| `inputSourceControl` | `inputSource` | `inputSource` | `TV`/`HDMI1‑4`/`AV1`/`COMPONENT1`/`USB`/`RVU`. Relevant to the Frame 2024 input-source gaps. |
| `directChannelControl` | `atvDtv` + `airCable` + `channelNum` | `channelNum` | All three required to tune a channel. |
| `channelUpDnControl` | `control` | `control` | `channelUp` / `channelDn`. |
| `directVolumeControl` | `volume` (0–100) | `volume` | Absolute volume. |
| `volumeUpDnControl` | `control` | `control` | `volumeUp` / `volumeDn`. |
| `muteControl` | `mute` | `mute` | `muteOn` / `muteOff`. |
| `pictureModeControl` | `pictureMode` | `pictureMode` | `Dynamic`/`Standard`/`Movie`/`Natural`/`HDR+`/`FilmmakerMode`. |
| `pictureSizeControl` | `pictureSize` | `pictureSize` | `16:9` / `4:3`. |
| `soundModeControl` | `soundMode` | `soundMode` | `Standard`/`Amplify`/`Optimized`/`ExternalStandard`. |
| `speakerSelectControl` | `speakerSelect` | `speakerSelect` | `Internal`/`External`/`AudioOut/Optical`. |
| `contrastControl` | `contrast` (0–100) | `contrast` | |
| `brightnessControl` | `brightness` (0–100) | `brightness` | |
| `sharpnessControl` | `sharpness` (0–100) | `sharpness` | |
| `colorControl` | `color` (0–100) | `color` | |
| `tintControl` | `tint` (−50–50) | `tint` | |
| `artModeControl` | `artMode` | `artMode` | `artModeOn` / `artModeOff`. **Explicit Art Mode toggle** — see below. |
| `directAccessControl` | `applicationName` *(+ optional `url`)* | — | Launch app: `webBrowser`/`netflix`/`amazon`/`pandora`/`vudu`/`youTube`/`hulu`. |
| `USBSourceControl` | `deviceId`, `deviceName` *(optional)* | — | |
| `RVUSourceControl` | `deviceId`, `deviceName` *(optional)* | — | |
| `externalSpeakerControl` | `deviceId`, `deviceName` *(optional)* | — | |

### RemoteKey values (`remoteKeyControl`)

`power`, `cursorUp`, `cursorDn`, `cursorLeft`, `cursorRight`, `menu`, `firstScreen`,
`enter`, `fastforward`, `rewind`, `play`, `stop`, `pause`, `return`, `exit`,
`number0`–`number9`, `caption`, `dash`, `red`, `green`, `yellow`, `blue`, `ambient`.

---

## Why this matters for the integration

Several methods map directly onto current pain points:

- **`powerControl`** — the explicit power-off (works from Art Mode) that the WebSocket
  `KEY_POWER` toggle can't deliver. Solves the no-SmartThings power-off issue. *This
  is the immediate target.*
- **`artModeControl`** — explicit `artModeOn`/`artModeOff`. Potentially more reliable
  than the current WS art path, and it closes the "`powerOn` lands in Art Mode" gap:
  `powerOn` → `artModeOff` gives a deterministic route to normal viewing.
- **`getTVStates`** — an authoritative state read (power, input, artMode, picture,
  sound, mute) independent of the WebSocket and SmartThings cloud — a candidate
  source for `is_on` / input / art-mode state that doesn't suffer the SmartThings
  cache lag or the frozen-WS-flag problem.
- **`inputSourceControl`** — direct input selection, where SmartThings returns an
  empty `supportedInputSources` on the Frame 2024.
- **`remoteKeyControl`** — a complete virtual remote, the natural fallback path if
  Samsung does disable ports 8001/8002 on a future firmware.

### Phasing suggestion

1. **Phase 1 (now):** `powerControl` on/off behind the opt-in pairing — solves the
   reported bug, minimal surface.
2. **Phase 2:** `getTVStates` as a state source, `artModeControl` for deterministic
   art-mode switching.
3. **Phase 3:** broader remote/input/picture control as a WebSocket fallback, should
   8001/8002 go away.

Each phase is independently shippable and degrades gracefully (no token → current
behaviour unchanged).
