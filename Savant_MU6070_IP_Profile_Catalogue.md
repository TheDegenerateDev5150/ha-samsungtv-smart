# Samsung IP Control — Savant MU6070 Profile Catalogue (`samsung_2017`)

Complete extraction of the **IP Control (JSON-RPC) surface** from a Savant /
Racepoint **Blueprint** driver for the Samsung **MU6070** series
(`UN(xx)MU6070`, aliases `UN50/UN58/UN65MU6070FXZA`), `device_class="HD monitor"`,
`<smart_tv_setup>samsung_2017</smart_tv_setup>`, profile change log up to v1.9.

This document is a **companion** to `IP_Control_Protocol_Reference.md` (the
authoritative empirical Frame 2024/2025 reference). It catalogues what a shipping
commercial control driver actually sends, and cross-references every method against
the Frame 2024 (`QE55LS03D`) findings.

> **Source & confidence:** extracted by OCR from 75 screenshots of the profile XML.
> Method names, value enums, response paths and timings below were cross-checked
> against the raw fragments. Items flagged *(OCR)* should be confirmed against the
> original capture before being relied on for an exact string.

> **Model-scope caveat (important):** this is a **2017 non-Frame TV** profile. It
> shares the **protocol** (JSON-RPC, `AccessToken` pairing) and most **method
> names** with the Frame, but the *implemented set differs*. Several methods that
> work here are `-32601 "Method not found"` on a Frame 2024 (see the delta table).
> The profile has **no Art Mode** methods at all (Art Mode is Frame-only) — for that,
> the empirical reference remains the only source.

---

## 1. Transport (per the Savant profile)

The profile sends each IP command as an HTTP `POST` whose body is a JSON-RPC 2.0
envelope (`http_request_type="POST"`, body parameters flagged `isHttpBody="true"`).
The transport **host/port is set at the Savant connection layer, not hard-coded in
the profile**, so the profile does not reveal the port — but the envelope shape,
the `AccessToken`-in-`params` pattern and the on-screen "Allow" pairing match the
**port 1516 JSON-RPC** service documented in the empirical reference.

### Request envelope

```json
{ "id": 1, "method": "<method>", "jsonrpc": "2.0", "params": { "AccessToken": "<token>", "<key>": "<value>" } }
```

- `createAccessToken` is sent with **no token** (and effectively no extra params).
- Every other method carries `AccessToken` inside `params`.
- A **getter** = the same method with the value key **omitted** (see §5).

---

## 2. Setup & pairing (per the Savant profile notes)

- **Wired LAN required.** "WiFi connection is not recommended."
- **WakeOnLAN required for PowerOn over IP** → MAC address must be provided in
  config (the profile cannot power on a fully-off TV via JSON-RPC alone; it relies
  on WoL, then talks IP).
- **Enable IP Remote on the TV:** `Home → Settings → General → Network →
  Expert Settings → "IP Remote" = Enable`.
- **Token retrieval (Blueprint ≥ 9.1):** System Monitor → *UPnP Discovery* → select
  the (powered-on) TV → **Get Token** → user has **30 s** to press **Allow** on the
  TV with the remote → token appears in the device info → paste into the
  `AccessToken` State Variable.
- The profile note states the token must be **re-entered after every re-upload**,
  and that once stored it persists — consistent with the empirical "token persists
  across power cycles" finding.

> Matches the empirical reference's pairing flow (`createAccessToken` → on-screen
> prompt → store token). The Savant note adds the **WoL-for-PowerOn** requirement
> explicitly.

---

## 3. Method catalogue (IP interface)

`AccessToken` is implied in `params` for every method except `createAccessToken`.

| Method | Param key | Param value(s) seen in profile | Driven by actions |
|---|---|---|---|
| `createAccessToken` | — | — (no params, no token) | `CreateAccessToken` |
| `powerControl` | `power` | `powerOn`, `powerOff` | `PowerOn`, `PowerOff`, `QueryPowerStatus` (getter) |
| `muteControl` | `mute` | `muteOn`, `muteOff` | `MuteOn`, `MuteOff`, `QueryMuteStatus` (getter) |
| `directVolumeControl` | `volume` | integer, **profile range 0–50** | `SetVolume`, `QueryVolumeStatus` (getter) |
| `volumeUpDnControl` | `control` | `volumeUp`, `volumeDn` | `IncreaseVolume`, `DecreaseVolume` |
| `channelUpDnControl` | `control` | `channelUp`, `channelDn` | `ChannelAnalogUp/Down`, `ChannelDigitalUp/Down` |
| `inputSourceControl` | `inputSource` | `HDMI1`, `HDMI2`, `HDMI3`, `HDMI4`, `TV`, `AV1`, `AV2`, `COMPONENT1`, `USB` | `SelectInput*` |
| `directAccessControl` | `applicationName` | `netflix`, `amazon`, `youtube`, `vudu`, `hulu`* | `Netflix`, `Amazon`, `Youtube`, `Vudu`, (`Hulu`*) |
| `remoteKeyControl` | `remoteKey` | see §4 | all virtual-remote keys |

\* `Hulu` is present but **commented out** (`<!-- ... -->`) in the source profile —
i.e. shipped disabled. App-name strings are **lowercase**.

> **Casing note:** the method is `muteControl` (lowercase `m`) — matches the Frame
> 2024 reference. Likewise `powerControl`, `directVolumeControl`, etc. are all
> lowercase-initial. (The empirical reference separately confirms `artModeControl`
> must be capital `M`; that method does not exist in this 2017 profile.)

---

## 4. `remoteKeyControl` — key values

Exact `remoteKey` strings observed in the profile (deduplicated):

```
cursorUp  cursorDn  cursorLeft  cursorRight  enter  return  exit
menu  firstScreen  play  pause  stop  rewind  fastforward
dash  red  green  blue  yellow  caption
number0 … number9
```

Notable per-action mappings in the profile:

- **`firstScreen`** is reused for `Home`, `Apps`, `Content`, and `MediaPlayer`
  (the profile has no distinct keys for those; they all open the Smart Hub / first
  screen).
- The lettered buttons map to colours: `ATriangle → red`, `BSquare → green`
  (and the colour actions `Red/Green/Blue/Yellow → red/green/blue/yellow`).
- `ClosedCaptions → caption`.
- Number actions (`NumberZero…NumberNine`) map to `number0…number9` *(OCR: the
  numeric value strings were the least legible fragments — the `number0–9` enum is
  corroborated by the empirical reference's py-samsungtv list).*

This enum is consistent with the `remoteKeyControl` value list in the empirical
reference — the Savant profile is independent corroboration that these are the
real, in-the-field key names.

---

## 5. Feedback / getter convention (the high-value part)

The profile implements three `Query*` polling actions. Each calls the **same
control method with the value key omitted**, then parses the result. This is the
"omit the param → it acts as a getter" convention.

| Query action | Method (body, getter form) | TV response shape | Profile mapping |
|---|---|---|---|
| `QueryPowerStatus` | `{"id":1,"method":"powerControl","jsonrpc":"2.0","params":{"AccessToken":"…"}}` | `{"result":{"power":"powerOn"\|"powerOff"}}` | `powerOn`→ON, `powerOff`→OFF |
| `QueryVolumeStatus` | `{"…","method":"directVolumeControl","params":{"AccessToken":"…"}}` | `{"result":{"volume":<int>}}` | integer → CurrentVolume |
| `QueryMuteStatus` | `{"…","method":"muteControl","params":{"AccessToken":"…"}}` | `{"result":{"mute":"muteOn"\|"muteOff"}}` | `muteOn`→ON, `muteOff`→OFF |

(The profile's response parser wraps the TV JSON under an object it names `none`,
so its internal paths read `/none/result/power`, `/none/result/volume`,
`/none/result/mute`, `/none/result/AccessToken`. On the wire it is just
`result.<field>`.)

> **Why this matters for the integration:** this is an independent, shipping-driver
> confirmation of the getter-by-param-omission convention — the same mechanism the
> empirical reference relies on for `artModeControl` (read) and `powerControl`
> (read). It strengthens the case for Phase 2 (`artModeControl` as the authoritative
> art-mode source) and shows the convention is the *intended* feedback path on this
> protocol family, not a Frame-specific quirk.

### Polling schedule the profile uses

- **Power:** continuous (`execute on schedule period.ms="0"`).
- **Volume & Mute:** every **5 minutes** (`period.ms="300000"`).

### Command timing the profile uses

- Inter-key delay: **200 ms** after remote keys.
- Power commands: **4000 ms** delay; PowerOn retry **10×** at **4500 ms**.
- Token "Allow" window: **30 s**.

---

## 6. Cross-reference: Savant 2017 profile vs Frame 2024 (empirical)

Status pulled from `IP_Control_Protocol_Reference.md`. "Delta" = where the 2017
profile and the Frame diverge, or where the profile adds something testable.

| Method | Savant 2017 | Frame 2024 (QE55LS03D) | Delta / action item |
|---|---|---|---|
| `createAccessToken` | ✅ | ✅ | Same pairing. Savant adds explicit **WoL-for-PowerOn**. |
| `powerControl` | ✅ on/off + getter | ✅ getter/setter (`+reboot`) | Aligned. Frame also accepts `reboot`. |
| `muteControl` | ✅ on/off + getter | ✅ getter/setter | Aligned (lowercase). |
| `directVolumeControl` | ✅ (range **0–50**) | ❌ `-32601` | **Delta:** absolute volume **gone on Frame**. Note Savant caps at **50**, vs py-samsungtv's 0–100. Use `volumeUpDnControl` / SmartThings on Frame. |
| `volumeUpDnControl` | ✅ `volumeUp/volumeDn` | ⚠️ needs param | Aligned — profile confirms the `control` values. |
| `channelUpDnControl` | ✅ `channelUp/channelDn` | ⚠️ needs param | Aligned — confirms `control` values. (Frames have no tuner; mostly moot.) |
| `inputSourceControl` | ✅ (HDMI1-4/TV/AV1/AV2/COMPONENT1/USB) | ❌ `-32601` | **Delta:** input switching **gone on Frame**. Read-only via `getTVStates.inputSource`; set via WS `KEY_HDMIx` / SmartThings. |
| `directAccessControl` | ✅ `applicationName` | ✅ | **Most actionable:** profile gives concrete app strings **`netflix` / `amazon` / `youtube` / `vudu`** (lowercase) — directly testable on the Frame, where the empirical ref knew only that the method works. |
| `remoteKeyControl` | ✅ (enum in §4) | ⚠️ needs param | Profile corroborates the real key names from a field deployment. `firstScreen` = Home. |
| `artModeControl` | — (not present) | ✅ getter/setter | Frame-only. Savant 2017 profile contributes nothing here. |
| `getTVStates` / `getVideoStates` | — (not used) | ✅ (7 / 5 fields) | Savant polls per-method getters (§5) instead of an aggregate state call. Two valid feedback styles. |

---

## 7. 2024 / 2025 behavioral deltas (cross-ecosystem)

The Savant MU6070 profile is a 2017 artifact. No public, raw, method-level profile
for a 2024/2025 Frame exists — the JSON-RPC `1516` surface lives inside proprietary
pro-control drivers (Savant, RTI, Control4, Crestron). A Savant `samsung_2024`
profile (the true XML equivalent of this document) exists but is **dealer-gated**
in the Blueprint library. The most detailed *public, 2024-aware* source is the
**RTI "Samsung IP Television" driver v1.09 (May 2024)**, which exposes behaviors
and config rather than the command table. The deltas below are drawn from it and
cross-checked against the empirical Frame 2024 reference.

> **Source provenance:** RTI Driver Store — "Samsung IP Television" v1.09, written
> against an MU7000, with an explicit pre-/post-2024 model-year switch. Behavioral
> notes only; RTI does not publish the raw JSON-RPC method strings.

| Area | Pre-2024 behavior | 2024 / 2025 behavior | Impact on the integration |
|---|---|---|---|
| **Port** | `1515` (pre-2020), `1516` (2020+) | `1516` | Confirms the transport already in use. |
| **Power-on path** | Wake-on-LAN packet to wake from deep sleep | **WoL removed** — power-on is **IP-direct** via `powerControl` + persistent token | On 2024/2025 Frames, WOL will not wake from deep sleep. `PowerOnMethod.WOL` is effectively dead on these models; rely on the stored IP token (matches the empirical "powerOn works on a fully-off TV with a stored token") or SmartThings. |
| **Pairing safety** | n/a | **Two "Deny" responses blacklist the controller** | Surface a clear warning in the pairing flow: the user must press **Allow**; denying twice can lock the controller out until reset. |
| **Art Mode + control** | — | **All IP control fails while Art Mode is on** (volume/color/contrast/etc.) until Art Mode is turned off | Confirms the #1 gotcha: pairing and setters time out in Art Mode. Gate IP setters on `artModeControl` reporting `artModeOff` first. |
| **Picture scales** | Standard variable set | **New variable set**: Brightness range **0–50** (not 0–100); **Tint = `R15`–`G15`** (non-numeric, button-stepped, no slider) | When reading `getVideoStates` on a Frame 2024/2025, interpret brightness on a 0–50 scale and treat tint as an R/G token, not an integer. |
| **Ambient mode** | `ambientModeControl` present in pre-2024 drivers | RTI still advertises ambient support | The empirical reference marks `ambientModeControl` as `-32601` on the QE55LS03D. The discrepancy is worth a **re-probe** — it may be model/firmware-dependent rather than universally absent. |

**Enable path (2024/2025, per RTI):** `Settings → General → Network → Expert →
IP Remote → Enable` (matches the empirical reference; menu wording varies by
firmware).

**Where the raw 2024 method table would come from, if needed:**

1. **Savant `samsung_2024` Blueprint profile** — the direct XML equivalent of this
   document; requires Savant dealer access to export.
2. **On-TV enumeration** (already done for the QE55LS03D) — remains the authoritative
   source for *what is actually implemented* on a given Frame.
3. The RTI driver package is downloadable but is a proprietary RTI bundle, not an
   open XML profile; readable-text extraction is uncertain.

---

## 8. Takeaways for the integration

1. **`directAccessControl` app names are now concrete** (`netflix`, `amazon`,
   `youtube`, `vudu`, lowercase) — probe these on the Frame; this is the one place
   the 2017 profile gives a directly usable string the empirical reference lacked.
2. **The getter convention is validated by an independent shipping driver** — omit
   the value key and read `result.<field>`. Reinforces Phase 2's use of
   `artModeControl` (read) as the authoritative art-mode source.
3. **Confirmed gaps are real, not accidental:** `directVolumeControl` and
   `inputSourceControl` being absent on the Frame is consistent with the profile's
   model family diverging — keep SmartThings / WS fallbacks for those.
4. **Timing & polling priors:** the profile's 200 ms key delay, 4000 ms power
   delay, continuous power poll and 5-min volume/mute poll are reasonable defaults
   to compare against the current 5 s scan / 10 s ST poll tuning.
5. **No Art Mode here.** For anything Art-Mode-related, the empirical Frame
   reference stays the single source of truth.
6. **2024/2025 power-on (§7):** WoL is gone on these models — power-on must use the
   persistent IP token (`powerControl`) or SmartThings, not a WOL packet. And warn
   users not to deny the pairing prompt (two denies blacklist the controller).

> Recommended next step (safe, per the established probing discipline): on a Frame,
> with a valid token and the TV in normal viewing (not Art Mode), send
> `directAccessControl` with `applicationName:"netflix"` and confirm launch, then
> read it back (getter) to see whether the Frame reports the launched app. A failed
> set returns an error without changing TV state, so probing is non-destructive.
