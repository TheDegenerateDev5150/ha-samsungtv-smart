# Samsung IP Control (JSON-RPC) — Protocol Reference

Consolidated reference for the undocumented JSON-RPC IP Control interface on recent
Samsung TVs, synthesised from four sources:

- **Empirical testing** on a Frame 2024 (`QE55LS03D`) and 2025 (`GQ50LS03F`).
- **On-TV method enumeration** run against the QE55LS03D (the source of truth for
  what is *actually* implemented on a consumer Frame — see "Confirmed on Frame
  2024" column below).
- The **`py-samsungtv`** clean-room library (method/param surface — note: this
  documents a broader API than what consumer Frames implement, see notes).
- Samsung's official **Wall PRO IP Command List** (API Wall v1.2), which exposes
  many of the same JSON-RPC method names for LED-wall displays.

**Important model-scope caveat:** Wall PRO (commercial LED panels) and consumer
Frame TVs share the **protocol** (JSON-RPC on port 1516) and method **names**, but
the **set of implemented methods is much smaller on Frame TVs**. Most picture /
sound / input setters documented in py-samsungtv and the Wall PRO PDF do not
exist on a Frame 2024 — they respond with `-32601 "Method not found"`. The table
below marks each method's status on the QE55LS03D.

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

Status column refers to behaviour observed on a Frame 2024 (QE55LS03D, Tizen 9)
when calling each method with only the `AccessToken` (no extra params):

- ✅ **OK** — returns a `result` with the field(s) shown.
- ⚠️ **needs param** — method exists but `-32602 "Invalid params"` without the
  setter-style argument.
- ❌ **not found** — `-32601 "Method not found"` on this model. Documented by
  py-samsungtv / Wall PRO but not implemented on consumer Frames.

| Method | Frame 2024 status | Setter param (when applicable) | Read returns | Notes |
|---|---|---|---|---|
| `createAccessToken` | ✅ (no token needed) | — | `AccessToken` | Pairing. Requires on-screen prompt; TV must be ON and NOT in Art Mode. |
| `getTVStates` | ✅ | — | `speakerSelect, volume, mute, pictureSize, pictureMode, soundMode, inputSource` | **7 fields, NOT the 10 py-samsungtv suggests.** No `power`, no `artMode`, no `atvDtv/airCable/channelNum` on Frame 2024. |
| `getVideoStates` | ✅ | — | `contrast, sharpness, brightness, color, tint` | **5 fields only.** Volume/pictureSize/soundMode/speakerSelect are in `getTVStates`, not here. |
| `powerControl` | ✅ getter/setter | `power` ∈ `powerOn` / `powerOff` / `reboot` | `power` | Read returns `powerOn` in Art Mode (Art Mode = physically on). Read-and-set via the same method. |
| `artModeControl` | ✅ getter/setter | `artMode` ∈ `artModeOn` / `artModeOff` | `artMode` | Case-sensitive: only `artModeControl` (capital M) works. `artmodeControl` / `ArtModeControl` → `-32601`. **Authoritative read-source for Art Mode state.** |
| `muteControl` | ✅ getter/setter | `mute` ∈ `muteOn` / `muteOff` | `mute` | |
| `directAccessControl` | ✅ getter/setter | `applicationName` (+ optional `url`) | `applicationName` | Launches an app. Read returns `"unknown"` when no app launched via this method. |
| `remoteKeyControl` | ⚠️ needs param | `remoteKey` (see list below) | — | Virtual remote key sender. |
| `volumeUpDnControl` | ⚠️ needs param | `control` ∈ `volumeUp` / `volumeDn` | `control` | Relative volume. |
| `channelUpDnControl` | ⚠️ needs param | `control` ∈ `channelUp` / `channelDn` | `control` | Relative channel. |
| `directVolumeControl` | ❌ | `volume` (0–100) | — | Absolute volume — **not implemented on Frame 2024**. Use `volumeUpDnControl` or SmartThings. |
| `inputSourceControl` | ❌ | `inputSource` | — | **Not implemented on Frame 2024.** Read-only via `getTVStates.inputSource`. To set input on a Frame: WebSocket `KEY_HDMIx` or SmartThings. |
| `pictureModeControl` | ❌ | `pictureMode` | — | Read-only via `getTVStates.pictureMode` on Frame 2024. |
| `pictureSizeControl` | ❌ | `pictureSize` | — | Read-only via `getTVStates.pictureSize`. |
| `soundModeControl` | ❌ | `soundMode` | — | Read-only via `getTVStates.soundMode`. |
| `speakerSelectControl` | ✅ | `speakerSelect` | `speakerSelect` | **Writable** (earlier "read-only" was wrong). Get with no params → capitalized value (`Internal`/`External`), unlike lowercase `getTVStates.speakerSelect`. Set accepts `Internal`, `AudioOut/Optical`; bare `External` is rejected — use `externalSpeakerControl`. |
| `externalSpeakerControl` | ✅ | `deviceName` + `deviceId` | JSON **array** of `{deviceName, deviceId}` | Get with no params lists reachable external audio devices (e.g. `[{"deviceName":"CINEMA 60(HDMI-eARC)","deviceId":"RCV-1"}]`; `{}` when the receiver is off). Set with a listed device switches output to it; unknown/unreachable device → `-32002`. |
| `contrastControl` / `brightnessControl` / `sharpnessControl` / `colorControl` / `tintControl` | ✅ | `<field>`: int | `<field>` | **Writable** (earlier "read-only" was wrong). Get with no params; set with `{"<field>": n}`. Ranges (Frame 2024/2025): contrast 0–50, color 0–50, sharpness 0–20, brightness −5…5, tint −15…15. Write is picture-mode gated → `-32002` in Dynamic/HDR-dynamic; Standard/Movie/Filmmaker accept it. |
| `directChannelControl` | ❌ | `atvDtv` + `airCable` + `channelNum` | — | Not implemented on Frame 2024 (Frames have no tuner anyway). |
| `USBSourceControl` / `RVUSourceControl` / `ambientModeControl` | ❌ | — | — | Not implemented on Frame 2024. May exist on other models. |

### RemoteKey values (`remoteKeyControl`)

`power`, `cursorUp`, `cursorDn`, `cursorLeft`, `cursorRight`, `menu`, `firstScreen`,
`enter`, `fastforward`, `rewind`, `play`, `stop`, `pause`, `return`, `exit`,
`number0`–`number9`, `caption`, `dash`, `red`, `green`, `yellow`, `blue`, `ambient`.

(Per py-samsungtv enums — exact validity per key TBD on Frame 2024.)

---

## Why this matters for the integration

Several methods map directly onto current pain points:

- **`powerControl`** — the explicit power-off (works from Art Mode) that the WebSocket
  `KEY_POWER` toggle can't deliver. Solves the no-SmartThings power-off issue.
  *Phase 1, shipped.*
- **`artModeControl`** — explicit `artModeOn`/`artModeOff` setter AND **authoritative
  read source** (call without `artMode` param → returns `{artMode: "artModeOn"}`).
  This is the **clean fix for the stale art-mode-after-power-off bug** on the Power
  switch / Frame Art Mode switch — instead of inferring art mode from `device_info`'s
  `PowerState`, we can query the TV directly. Also lets us implement a deterministic
  "wake to normal viewing" via `powerOn` → `artModeOff`.
- **`getTVStates` / `getVideoStates`** — read-only snapshots of input source, mute,
  picture/sound modes and levels, on Frame 2024. Useful for sensor entities or as a
  cross-check; **not** the source for `power` or `artMode` state (those fields are
  absent — use `powerControl`/`artModeControl` instead).
- **`muteControl`** — the only mute setter that works via IP Control on Frame 2024.

### What we cannot do via IP Control on Frame 2024 (per empirical enumeration)

- Set input source (`inputSourceControl` → not found). Use WS `KEY_HDMIx` or
  SmartThings.
- Set picture mode / picture size / sound mode / speaker / picture levels — all
  `-32601`. Read-only via `getTVStates`/`getVideoStates`. Use SmartThings for setting.
- Set absolute volume (`directVolumeControl` → not found). Only `volumeUpDnControl`
  works. Use SmartThings for absolute volume.

So IP Control on a consumer Frame is essentially a **power + art-mode + virtual
remote + app launcher + readout** API. Not a full replacement for SmartThings or
WebSocket — but exactly what we needed for the painful gaps (power off / art mode
state).

### Phasing

1. **Phase 1 (shipped):** `powerControl` on/off behind opt-in pairing.
2. **Phase 2 (next):** `artModeControl` (read) as the authoritative art-mode source —
   replaces the `device_info.PowerState='standby'` workaround we shipped in the
   media_player `art_mode_status` calc. Plus `artModeControl` (write) for
   deterministic art-mode toggling.
3. **Phase 3:** `remoteKeyControl` virtual remote as a WS-port fallback should
   Samsung ever disable 8001/8002. Volume up/down too if relevant.

Each phase is independently shippable and degrades gracefully (no token → current
behaviour unchanged).
