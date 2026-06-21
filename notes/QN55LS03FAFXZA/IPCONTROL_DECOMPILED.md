# Samsung IP Control 1515/1516 Decompile Notes

Device/firmware context:

- Model: `QN55LS03FAFXZA`
- Samsung support/downloads: <https://www.samsung.com/us/support/downloads/?model=N0003009&modelCode=QN55LS03FAFXZA>
- Firmware: `T-PTMFAKUC-0090-1296.8`
- Documented: `2026-06-18`
- Tizen: `9.0.0`
- Linux: `5.4.261 armv7l`
- TV-reported product model: `LS03F_PM`

Sources pulled from the TV:

- `/opt/usr/apps/com.samsung.tv.mde-framework/bin/mde-framework`
- `/opt/usr/apps/com.samsung.tv.mde-framework/lib/libmde-protocol-ipcontrol.so`
- `/usr/apps/org.tizen.ipcontrol/libipcontrol-http-server.so`

Decompile dumps were generated locally from those pulled binaries.

## Owner

`1516` is served by:

```text
/opt/usr/apps/com.samsung.tv.mde-framework/bin/mde-framework
appid com.samsung.tv.mde-framework
onboot=true, autorestart=true
```

`mde-framework` links `libmde-protocol-ipcontrol.so`, which loads
`/usr/apps/org.tizen.ipcontrol/libipcontrol-http-server.so`.

Port logic:

```c
GetTVYear() < 20 ? 1515 : 1516
```

This TV is on `1516`.

## HTTPS Transport

`libipcontrol-http-server.so` implements a tiny Boost.Asio/OpenSSL HTTP server.

Accepts:

- `POST`
- `HTTP/1.0` or `HTTP/1.1`
- any request target; no route/path dispatch was found
- required headers:
  - `Content-Type` containing `application/json`
  - `Accept` containing `application/json`
  - `Host`
  - `Content-Length`

Rejects/does not support:

- `GET`, `HEAD`, etc.
- HTTP versions other than 1.0/1.1
- `Transfer-Encoding: chunked`
- WebSocket upgrade; no WS parser/dispatcher in this server

Response banner:

```http
Server: Samsung IP Control Server/1.0
Content-Type: application/json; charset="utf-8"
```

TLS cert observed: `CN = Samsung IP Control G2`.

## JSON-RPC Envelope

Body must parse as JSON and contain:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "getTVStates",
  "params": {
    "AccessToken": "..."
  }
}
```

Parser facts:

- body must start with `{` or `[`
- `jsonrpc` must be exactly `"2.0"`
- `method` is read with `JsonValue::asString()`
- `id` is read with `JsonValue::asString()`
- `params.AccessToken` is required for everything except `createAccessToken`

Auth flow:

- `createAccessToken` bypasses token auth
- service gets peer MAC from the HTTP session
- denied MAC group is checked first
- token issue path calls notification/UI code
- returned result shape is `{ "AccessToken": "..." }`
- other methods call `getAccessToken()` and check auth group
- `getAccessToken` / `removeAccessToken` are parser helpers, not JSON-RPC methods

Set-vs-get:

- `params` containing only `AccessToken` is treated as a get operation
- any non-`AccessToken` member makes it a set operation
- some `get*` methods are get-only

## JSON-RPC Params

Every method except `createAccessToken` still needs `params.AccessToken`.
For a get, pass no method-specific params. For a set, pass one of the keys below.

Example:

```json
{"jsonrpc":"2.0","id":"1","method":"backlightControl","params":{"AccessToken":"..."}}
{"jsonrpc":"2.0","id":"2","method":"backlightControl","params":{"AccessToken":"...","backlight":25}}
```

Normal TV params:

| method | set params | notes |
| --- | --- | --- |
| `ambientControl` | `ambientId` string | wall/microLED map |
| `artModeControl` | `artMode` string | `artModeOn` is special: emits `/v2/powerValue` with `{"mode":"ambient"}` |
| `brightnessControl` | `brightness` int | |
| `channelUpDnControl` | `control` string | expected `channelUp` or `channelDn`; helper accepts any key alias below |
| `colorControl` | `color` int | |
| `contrastControl` | `contrast` int | |
| `directAccessControl` | `applicationName` string | mapped to app id; known built-ins include `youTube`, `netflix`, `amazon` |
| `directChannelControl` | `atvDtv` string, `airCable` string, `channelNum` string | converted internally to `channelType`, `RFtype`, `channelNumber` |
| `directVolumeControl` | `volume` int | direct absolute volume, `0..100` |
| `displayRotatorControl` | `orientation` string | accepts `portrait` or `landscape`; result uses `Portrait`/`Landscape` |
| `externalSpeakerControl` | `deviceName` string, `deviceId` string | builds internal JSON with `id`/name |
| `firstScreenAppControl` | `applicationName` string | no extra params queries first-screen apps/state |
| `getBoxStates` | none | get-only |
| `getCabinetGroupIds` | none | get-only |
| `getCabinetStates` | `groupId` int | wall/microLED map |
| `getDeviceInformation` | none | get-only; result includes `modelID`, `serialNumber`, `FWVersion` |
| `getTVStates` | none | get-only; result is postprocessed TV state, including source/mute fields when present |
| `getVideoStates` | none | get-only; result has `contrast`, `sharpness`, `brightness`, `color` |
| `inputSourceControl` | `inputSource` string | value passed through; TV is normalized internally |
| `multiviewControl` | `multiviewMode` string | no extra params queries supported/current modes |
| `muteControl` | `mute` string | `muteOn` or `muteOff`; `getTVStates` is the clean mute getter |
| `pictureModeControl` | `pictureMode` string | value passed through |
| `pictureSizeControl` | `pictureSize` string | value passed through |
| `powerControl` | `power` string | accepts `powerOn`, `powerOff`, `reboot`, `force-reboot` |
| `remoteKeyControl` | `remoteKey` string | helper maps alias to Samsung `KEY_*` and sends `pressAndRelease` |
| `sharpnessControl` | `sharpness` int | |
| `soundModeControl` | `soundMode` string | value passed through |
| `speakerSelectControl` | `speakerSelect` string | public values are `Internal`, `External`, `AudioOut/Optical`; helper rewrites to internal values |
| `tintControl` | `tint` int | |
| `USBSourceControl` | `deviceName` string, `deviceId` string | helper sends `deviceId` as internal `additionalData` |
| `volumeUpDnControl` | `control` string | expected `volumeUp` or `volumeDn`; helper accepts any key alias below |

Remote/key aliases accepted by `control` and `remoteKey`:

```text
power cursorUp cursorDn cursorLeft cursorRight menu firstScreen enter
fastforward rewind play stop pause return exit
number1 number2 number3 number4 number5 number6 number7 number8 number9 number0
caption dash red green yellow blue ambient channelUp channelDn volumeUp volumeDn multiview
```

Expert-picture params:

```text
pictureCalibrationModeControl -> pictureCalibrationMode (string)
backlightControl -> backlight (int)
digitalCleanViewControl -> digitalCleanView (string)
autoMotionPlusControl -> autoMotionPlus (string)
AMP.blurReductionControl -> AMP.blurReduction (int)
AMP.judderReductionControl -> AMP.judderReduction (int)
AMP.LEDClearMotionControl -> AMP.LEDClearMotion (string)
localDimmingControl -> localDimming (string)
filmModeControl -> filmMode (string)
contrastEnhancerControl -> contrastEnhancer (string)
colorToneControl -> colorTone (string)
WB2PointControl -> special: all non-AccessToken params are serialized as the WB2Point JSON string
WB20PointModeControl -> WB20PointMode (string)
WB20P.IntervalControl -> WB20P.Interval (string)
WB20P.RedControl -> WB20P.Red (int)
WB20P.GreenControl -> WB20P.Green (int)
WB20P.BlueControl -> WB20P.Blue (int)
gammaModeControl -> gammaMode (string)
gamma.BT1886Control -> gamma.BT1886 (int)
gamma.ST2084Control -> gamma.ST2084 (int)
gamma.HLGControl -> gamma.HLG (int)
RGBOnlyModeControl -> RGBOnlyMode (string)
colorSpaceControl -> colorSpace (string)
colorSpace.ColorControl -> colorSpace.Color (string)
colorSpace.ColorAdjustmentPointControl -> colorSpace.ColorAdjustmentPoint (string)
colorSpace.RedControl -> colorSpace.Red (int)
colorSpace.GreenControl -> colorSpace.Green (int)
colorSpace.BlueControl -> colorSpace.Blue (int)
HDRToneMappingControl -> HDRToneMapping (string)
colorSpaceGamutControl -> colorSpaceGamut (string)
peakBrightnessControl -> peakBrightness (string)
colorBoosterControl -> colorBooster (string)
autoHDRRemasteringControl -> autoHDRRemastering (string)
brightnessOptimizationControl -> brightnessOptimization (string)
energySavingSolutionControl -> energySavingSolution (string)
gameModeControl -> gameMode (string)
applyPictureSettingsControl -> applyPictureSettings (string)
motionLightingControl -> motionLighting (string)
autoPowerSavingControl -> autoPowerSaving (string)
autoPowerOffControl -> autoPowerOff (string)
pixelShiftMenuControl -> pixelShiftMenu (string)
```

AV/soundbar params:

| method | set params | notes |
| --- | --- | --- |
| `getCodec` | none | get-only, returns `codec` |
| `getIdentifier` | none | get-only, returns `identifier` |
| `getIPControlState` | none | get-only, returns `ipcontrolState` |
| `getMute` | none | get-only, returns `mute` |
| `getVolume` | none | get-only, returns `volume` |
| `inputSelectControl` | `inputSource` string | |
| `muteControl` | `mute` bool | AV path uses bool, not normal-TV `muteOn`/`muteOff` |
| `powerControl` | `power` string | |
| `remoteKeyControl` | `remoteKey` string | |
| `soundModeControl` | `soundMode` string | |
| `volumeControl` | `volume` int | |

HTV params are not decoded per method in this library. `HTVMDEFHandler` forwards
the full params JSON as `setCommand` when any non-`AccessToken` member exists,
otherwise as `getCommand`; the external HTV service owns the method-specific
schema.

## QN55LS03FAFXZA Method Reference And Live Evidence

This section combines the decompiled method maps with live behavior observed on
`QN55LS03FAFXZA` on `2026-06-18`. The goal is a usable reference for every
known JSON-RPC function.

Mode note: the none-ambient controls below were validated while the TV was in
normal TV mode. In Art/Ambient modes some none-ambient methods can disappear
from dispatch or return `-32601 Method not found`.

Baseline state:

```json
{
  "getDeviceInformation": {
    "modelID": "25_PTM_FTV",
    "FWVersion": "T-PTMFAKUC-0090-1296.8",
    "serialNumber": "<redacted>"
  },
  "getTVStates": {
    "inputSource": "TV",
    "mute": "muteOff",
    "pictureMode": "Standard",
    "pictureSize": "16:9",
    "soundMode": "Standard",
    "speakerSelect": "internal",
    "volume": 0
  },
  "getVideoStates": {
    "brightness": 0,
    "color": 15,
    "contrast": 50,
    "sharpness": 10,
    "tint": 0
  }
}
```

Legend: ✅ works on this TV/state, ⚠️ method exists but the listed operation is partial or state-dependent, ❌ failed on this TV/state, `decompiled` means the method/params came from the binary but were not live-validated in this state.

### Auth

| Method | Params / Values | Live Evidence | Notes |
| --- | --- | --- | --- |
| `createAccessToken` | no `AccessToken` required | ✅ returns `{"AccessToken":"..."}` | Pairing/token issuance path. Other methods require `params.AccessToken`. |

### Normal / Open Methods

| Method | Params / Values | Live Evidence | Notes |
| --- | --- | --- | --- |
| `artModeControl` | `artMode`: `artModeOn`, `artModeOff` | ✅ getter/setter supported | `artModeOn` emits `/v2/powerValue` with `{"mode":"ambient"}` internally. |
| `channelUpDnControl` | `control`: `channelUp`, `channelDn` | ✅ `channelUp` accepted; no-param call returns `-32602` | Remote-key style setter, not a getter. |
| `directAccessControl` | `applicationName`: e.g. `youTube`, `netflix`, `amazon`; optional URL/deeplink | ✅ `youTube` accepted | Direct app launch path. |
| `displayRotatorControl` | `orientation`: `landscape`, `portrait` | ✅ both accepted | Getter returns `Landscape`/`Portrait`; setter wants lowercase. |
| `firstScreenAppControl` | `applicationName` display/app alias | ✅ getter returns installed app list; sample setter returned `-32002` | Getter returned apps including Apple TV, Disney+, Hulu, Netflix, Prime Video, Plex, SmartThings, Spotify, YouTube, YouTube TV. |
| `getDeviceInformation` | none | ✅ `{"modelID":"25_PTM_FTV","FWVersion":"T-PTMFAKUC-0090-1296.8","serialNumber":"<redacted>"}` | Device identity getter. |
| `getTVStates` | none | ✅ `{"inputSource":"TV","mute":"muteOff","pictureMode":"Standard","pictureSize":"16:9","soundMode":"Standard","speakerSelect":"internal","volume":0}` | Baseline TV state getter. |
| `getVideoStates` | none | ✅ `{"brightness":0,"color":15,"contrast":50,"sharpness":10,"tint":0}` | Baseline video state getter. |
| `multiviewControl` | `multiviewMode`: values are state-dependent | ⚠️ getter returned `[]`; `Off`/`On` setters returned `-32002` | Method exists but no supported/current modes were returned in this state. |
| `muteControl` | `mute`: `muteOff`, `muteOn` | ✅ both values accepted | Getter returns `mute`. |
| `powerControl` | `power`: `powerOn`, `powerOff`, `reboot`, `force-reboot` | ✅ `powerOn` getter/setter works | `powerOff`, `reboot`, and `force-reboot` are decompiled values; they are intentionally dangerous but still part of the API. |
| `remoteKeyControl` | `remoteKey`: aliases listed below | ✅ `return` accepted; no-param call returns `-32602` | Remote-key style setter, not a getter. |
| `volumeUpDnControl` | `control`: `volumeUp`, `volumeDn` | ✅ `volumeUp` accepted; no-param call returns `-32602` | Remote-key style setter, not a getter. |

### Normal / None-Ambient Methods

| Method | Params / Values | Live Evidence | Notes |
| --- | --- | --- | --- |
| `brightnessControl` | `brightness`: int | ✅ accepted `-5..5` | This is picture brightness, not panel backlight. |
| `colorControl` | `color`: int | ✅ accepted `0..50` |  |
| `contrastControl` | `contrast`: int | ✅ accepted `0..50` | Absolute picture contrast. |
| `directChannelControl` | `atvDtv`, `airCable`, `channelNum` | ✅ getter returned `{"airCable":"cable","atvDtv":"tvplus","channelNum":"1001"}`; sample DTV/AIR/1 returned `-32002` | Converts to internal `channelType`, `RFtype`, `channelNumber`. |
| `directVolumeControl` | `volume`: int `0..100` | ✅ accepted `0..100` | Absolute volume. |
| `externalSpeakerControl` | `deviceName`, `deviceId` | ✅ getter returned `{}`; fake device setter returned `-32002` | Real setter needs a valid external speaker device. |
| `inputSourceControl` | `inputSource`: `TV`; HDMI values appear source/state-dependent | ✅ `TV` accepted; `HDMI1`..`HDMI4` rejected in this state | Connected/available inputs likely affect setter success. |
| `pictureModeControl` | `pictureMode`: `Dynamic`, `Standard`, `Movie` | ✅ accepted; `Filmmaker Mode` rejected | Values from live string exploration. |
| `pictureSizeControl` | `pictureSize`: decompiled pass-through string | ✅ getter returned `16:9`; tested `16:9`, `4:3`, `Fit to Screen` setters returned `-32002` | Setter appears state/input dependent or uses different strings. |
| `sharpnessControl` | `sharpness`: int | ✅ accepted `0..20` |  |
| `soundModeControl` | `soundMode`: `Standard`, `Amplify`, `Movie`, `Music` | ✅ accepted; `Adaptive Sound` rejected | Values from live string exploration. |
| `speakerSelectControl` | `speakerSelect`: `Internal`, `AudioOut/Optical` | ✅ accepted; `External`, `Optical` rejected | Getter may normalize case; helper rewrites to internal speaker values. |
| `tintControl` | `tint`: int | ✅ accepted `-15..15` |  |
| `USBSourceControl` | `deviceName`, `deviceId` | ✅ getter returned `[]`; fake device setter returned `-32002` | Real setter needs a valid USB source. |

### Expert Picture Methods

| Method | Params / Values | Live Evidence | Notes |
| --- | --- | --- | --- |
| `AMP.blurReductionControl` | `AMP.blurReduction`: int | ✅ getter returned `10`; same-value setter returned `-32002` | Usually gated by Auto Motion Plus custom state. |
| `AMP.judderReductionControl` | `AMP.judderReduction`: int | ✅ getter returned `10`; same-value setter returned `-32002` | Usually gated by Auto Motion Plus custom state. |
| `AMP.LEDClearMotionControl` | `AMP.LEDClearMotion`: `Off`, `On` | ✅ getter returned `Off`; tested setters returned `-32002` | Usually gated by Auto Motion Plus custom state. |
| `applyPictureSettingsControl` | `applyPictureSettings`: `CurrentSource`, `AllSources` | ✅ accepted; strings with spaces rejected |  |
| `autoHDRRemasteringControl` | `autoHDRRemastering`: `Off`, `On` | ✅ accepted |  |
| `autoMotionPlusControl` | `autoMotionPlus`: `Off`, `Auto`, `Custom` | ✅ accepted; `Standard` rejected |  |
| `autoPowerOffControl` | `autoPowerOff`: `Off`, `On` candidates | ✅ `Off` accepted; `On` returned `-32002` | Power behavior; state/model dependent. |
| `autoPowerSavingControl` | `autoPowerSaving`: `Off`, `On` | ✅ `Off` accepted; `On` accepted in live evidence | Power/eco behavior; method remains documented from decompile and live evidence. |
| `backlightControl` | `backlight`: int | ✅ accepted `0..50` | Separate from Art Mode brightness. |
| `brightnessOptimizationControl` | `brightnessOptimization`: `Off`, `On` | ✅ accepted |  |
| `colorBoosterControl` | `colorBooster`: `Off`, `Low`, `High` candidates | ❌ getter/setters returned `-32002` | Method exists in decompiled map. |
| `colorSpace.BlueControl` | `colorSpace.Blue`: int | ✅ getter returned `50`; same-value setter returned `-32002` | Likely custom color-space only. |
| `colorSpace.ColorAdjustmentPointControl` | `colorSpace.ColorAdjustmentPoint`: `Red`, `Green`, `Blue`, `Yellow`, `Cyan`, `Magenta` candidates | ❌ getter/setters returned `-32002` | Likely custom color-space only. |
| `colorSpace.ColorControl` | `colorSpace.Color`: `Red`, `Green`, `Blue`, `Yellow`, `Cyan`, `Magenta` candidates | ✅ getter returned `Red`; tested setters returned `-32002` | Likely requires `colorSpace=Custom`. |
| `colorSpace.GreenControl` | `colorSpace.Green`: int | ✅ getter returned `53`; same-value setter returned `-32002` | Likely custom color-space only. |
| `colorSpace.RedControl` | `colorSpace.Red`: int | ✅ getter returned `40`; same-value setter returned `-32002` | Likely custom color-space only. |
| `colorSpaceControl` | `colorSpace`: `Auto`, `Native`, `Custom` | ✅ accepted |  |
| `colorSpaceGamutControl` | `colorSpaceGamut`: `BT.709`, `DCI-P3`, `BT.2020`, `Auto` candidates | ✅ getter returned `BT.709`; tested setters returned `-32002` | HDR/color-space state dependent. |
| `colorToneControl` | `colorTone`: `Cool`, `Standard`, `Warm1`, `Warm2` | ✅ accepted | This is the verified color-tone enum for this TV. |
| `contrastEnhancerControl` | `contrastEnhancer`: `Off`, `Low`, `High` | ✅ accepted |  |
| `digitalCleanViewControl` | `digitalCleanView`: candidates `Off`, `Auto`, `Low`, `Medium`, `High`, `Standard` | ✅ getter returned `Standard`; tested setters returned `-32002` | Getter works; setter is state/input dependent or values differ. |
| `energySavingSolutionControl` | `energySavingSolution`: `Off`; candidates `Low`, `Medium`, `High`, `Auto` rejected | ✅ `Off` accepted | Other values may be region/eco-mode dependent. |
| `filmModeControl` | `filmMode`: `Off`, `Auto1`, `Auto2` | ✅ getter returned `Off`; tested setters returned `-32002` | Input/content dependent. |
| `gameModeControl` | `gameMode`: `Off`, `On`, `Auto` candidates | ✅ getter returned `Off`; tested setters returned `-32002` | Input/source dependent. |
| `gamma.BT1886Control` | `gamma.BT1886`: int | ✅ accepted `-3..3` |  |
| `gamma.HLGControl` | `gamma.HLG`: int | ❌ getter/setter returned `-32002` | HDR/content dependent. |
| `gamma.ST2084Control` | `gamma.ST2084`: int | ❌ getter/setter returned `-32002` | HDR/content dependent. |
| `gammaModeControl` | `gammaMode`: `BT.1886`; candidates `ST.2084`, `HLG` rejected in this SDR state | ✅ `BT.1886` accepted | HDR gamma modes are content/state dependent. |
| `HDRToneMappingControl` | `HDRToneMapping`: decompiled string; candidates `0`, `1`, `Static`, `Active` | ✅ getter returned `0`; tested setters returned `-32002` | HDR/content dependent. |
| `localDimmingControl` | `localDimming`: `Off`, `Low`, `Standard`, `High` candidates | ❌ getter/setters returned `-32002` | Method exists in decompiled map. |
| `motionLightingControl` | `motionLighting`: `Off`, `On` | ✅ accepted |  |
| `peakBrightnessControl` | `peakBrightness`: `Off`, `Medium`, `High` candidates | ❌ getter/setters returned `-32002` | HDR/state dependent. |
| `pictureCalibrationModeControl` | `pictureCalibrationMode`: `Off`, `On` candidates | ❌ getter/setters returned `-32002` | Method exists in decompiled expert-picture map. |
| `pixelShiftMenuControl` | `pixelShiftMenu`: `Off`, `On` candidates | ❌ getter/setters returned `-32002` | OLED/panel-feature dependent. |
| `RGBOnlyModeControl` | `RGBOnlyMode`: `Off`, `Red`, `Green`, `Blue` candidates | ❌ getter/setters returned `-32002` | Method exists in decompiled map. |
| `WB20P.BlueControl` | `WB20P.Blue`: int | ✅ getter returned `0`; same-value setter returned `-32002` | Likely gated by 20-point mode. |
| `WB20P.GreenControl` | `WB20P.Green`: int | ✅ getter returned `0`; same-value setter returned `-32002` | Likely gated by 20-point mode. |
| `WB20P.IntervalControl` | `WB20P.Interval`: `5%`..`100%` candidates | ✅ getter returned `5%`; tested setters returned `-32002` | Likely requires `WB20PointMode=On` or a specific picture state. |
| `WB20P.RedControl` | `WB20P.Red`: int | ✅ getter returned `0`; same-value setter returned `-32002` | Likely gated by 20-point mode. |
| `WB20PointModeControl` | `WB20PointMode`: `Off`, `On` | ✅ accepted |  |
| `WB2PointControl` | `R-Gain`, `G-Gain`, `B-Gain`, `R-Offset`, `G-Offset`, `B-Offset` ints | ✅ getter/same-value setter worked | All non-token params are serialized as the WB2Point JSON string. |

### Wall / MicroLED Methods

| Method | Params / Values | Live Evidence | Notes |
| --- | --- | --- | --- |
| `ambientControl` | `ambientId`: string | ❌ `-32601` | Wall/microLED map only. |
| `getBoxStates` | none | ❌ `-32601` | Wall/microLED getter. |
| `getCabinetGroupIds` | none | ❌ `-32601` | Wall/microLED getter. |
| `getCabinetStates` | `groupId`: int | ❌ `-32601` | Wall/microLED getter requiring group id. |

### AV / Soundbar Methods

These methods are selected when the same library detects an AV/soundbar device
type instead of normal TV.

| Method | Params / Values | Live Evidence On This TV | Notes |
| --- | --- | --- | --- |
| `getCodec` | none | ❌ `-32601` | Soundbar-only getter. |
| `getIdentifier` | none | ❌ `-32601` | Soundbar-only getter. |
| `getIPControlState` | none | ❌ `-32601` | Soundbar-only getter. |
| `getMute` | none | ❌ `-32601` | Soundbar-only getter. |
| `getVolume` | none | ❌ `-32601` | Soundbar-only getter. |
| `inputSelectControl` | `inputSource`: string | ❌ `-32601` | Soundbar-only on this TV. |
| `muteControl` | `mute`: bool | normal-TV method uses `muteOn`/`muteOff`; AV-specific bool dispatch not selected on this TV | AV path uses bool instead of the normal-TV string enum. |
| `powerControl` | `power`: string | normal-TV method works; AV-specific dispatch not selected on this TV | Shared method name; AV manager has its own property map. |
| `remoteKeyControl` | `remoteKey`: string | normal-TV method works; AV-specific dispatch not selected on this TV | Shared method name; AV manager has its own property map. |
| `soundModeControl` | `soundMode`: string | normal-TV method works; AV-specific dispatch not selected on this TV | Shared method name; AV manager has its own property map. |
| `volumeControl` | `volume`: int | ❌ `-32601` | Soundbar-only on this TV. |

### HTV Methods

These are in the decompiled HTV map. On this consumer Frame TV they return
`-32601 Method not found`.

| Method | Params / Values |
| --- | --- |
| `duplicateHTVConfigControl` | full params JSON forwarded to HTV service |
| `forwardMessage` | full params JSON forwarded to HTV service |
| `getHTVInformation` | full params JSON forwarded to HTV service |
| `getHTVNetworkInformation` | full params JSON forwarded to HTV service |
| `getSoftAPSecurityKey` | full params JSON forwarded to HTV service |
| `HTVFactoryLockControl` | full params JSON forwarded to HTV service |
| `HTVRoomStatusControl` | full params JSON forwarded to HTV service |
| `setHTVTime` | full params JSON forwarded to HTV service |
| `showHTVNotification` | full params JSON forwarded to HTV service |
| `softAPSignalLevelControl` | full params JSON forwarded to HTV service |
| `softAPSSIDControl` | full params JSON forwarded to HTV service |
| `softAPStatusControl` | full params JSON forwarded to HTV service |
| `softAPWiFiChannelControl` | full params JSON forwarded to HTV service |
| `tvPlusDisable` | full params JSON forwarded to HTV service |
| `updateFirmware` | full params JSON forwarded to HTV service |


Response shape:

```json
{"jsonrpc":"2.0","id":"1","result":{...}}
```

or:

```json
{"jsonrpc":"2.0","id":"1","error":{"code":-32601,"message":"Method not found"}}
```

Compiled error templates:

- `-32000 Server error / Unknown`
- `-32001 Server error / Not supported model`
- `-32002 Server error / Failed`
- `-32003 Server error / Invalid operation`
- `-32004 Server error / No support for batch request`
- `-32010 Unauthorized access`
- `-32011 All AccessToken occupied`
- `-32600 Invalid Request`
- `-32601 Method not found`
- `-32602 Invalid params`
- `-32603 Internal error`
- `-32700 Parse error`

## Normal TV JSON-RPC Methods

Device type selection:

- HTV product -> `HTVManager`
- soundbar -> `AVManager`
- normal TV -> `TVManager` + `MDEFHandler`

Normal TV lookup order:

- if wall/microLED: search wall map
- if not ambient mode: search none-ambient map
- always search open map

The expert-picture map is inserted into the same open map.

Open map:

- `artModeControl`
- `channelUpDnControl`
- `directAccessControl`
- `displayRotatorControl`
- `firstScreenAppControl`
- `getDeviceInformation`
- `getTVStates`
- `getVideoStates`
- `multiviewControl`
- `muteControl`
- `powerControl`
- `remoteKeyControl`
- `volumeUpDnControl`

Expert-picture entries in open map:

- `AMP.blurReductionControl`
- `AMP.judderReductionControl`
- `AMP.LEDClearMotionControl`
- `applyPictureSettingsControl`
- `autoHDRRemasteringControl`
- `autoMotionPlusControl`
- `autoPowerOffControl`
- `autoPowerSavingControl`
- `backlightControl`
- `brightnessOptimizationControl`
- `colorBoosterControl`
- `colorSpace.BlueControl`
- `colorSpace.ColorAdjustmentPointControl`
- `colorSpace.ColorControl`
- `colorSpace.GreenControl`
- `colorSpace.RedControl`
- `colorSpaceControl`
- `colorSpaceGamutControl`
- `colorToneControl`
- `contrastEnhancerControl`
- `digitalCleanViewControl`
- `energySavingSolutionControl`
- `filmModeControl`
- `gameModeControl`
- `gamma.BT1886Control`
- `gamma.HLGControl`
- `gamma.ST2084Control`
- `gammaModeControl`
- `HDRToneMappingControl`
- `localDimmingControl`
- `motionLightingControl`
- `peakBrightnessControl`
- `pictureCalibrationModeControl`
- `pixelShiftMenuControl`
- `RGBOnlyModeControl`
- `WB20P.BlueControl`
- `WB20P.GreenControl`
- `WB20P.IntervalControl`
- `WB20P.RedControl`
- `WB20PointModeControl`
- `WB2PointControl`

None-ambient map:

- `brightnessControl`
- `colorControl`
- `contrastControl`
- `directChannelControl`
- `directVolumeControl`
- `externalSpeakerControl`
- `inputSourceControl`
- `pictureModeControl`
- `pictureSizeControl`
- `sharpnessControl`
- `soundModeControl`
- `speakerSelectControl`
- `tintControl`
- `USBSourceControl`

Wall map:

- `ambientControl`
- `getBoxStates`
- `getCabinetGroupIds`
- `getCabinetStates`

Not present as exact strings in this pulled library:

- `ambientModeControl`
- `RVUSourceControl`

## HTV JSON-RPC Methods

HTV-specific map:

- `duplicateHTVConfigControl`
- `forwardMessage`
- `getHTVInformation`
- `getHTVNetworkInformation`
- `getSoftAPSecurityKey`
- `HTVFactoryLockControl`
- `HTVRoomStatusControl`
- `setHTVTime`
- `showHTVNotification`
- `softAPSignalLevelControl`
- `softAPSSIDControl`
- `softAPStatusControl`
- `softAPWiFiChannelControl`
- `tvPlusDisable`
- `updateFirmware`

## AV/Soundbar JSON-RPC Methods

Only selected when `SystemInfoUtil::IsSoundbar()` makes device type `AV`.

AV property map:

- `getCodec`
- `getIdentifier`
- `getIPControlState`
- `getMute`
- `getVolume`
- `inputSelectControl`
- `muteControl`
- `powerControl`
- `remoteKeyControl`
- `soundModeControl`
- `volumeControl`

## UPnP In Same Module

This is adjacent to, not the 1516 HTTPS JSON-RPC transport.

Device/service description strings:

- device type: `urn:samsung.com:device:IPControlServer:1`
- service type: `urn:samsung.com:service:IPControlService:1`
- control URL: `/upnp/control/IPControlService1`
- event URL: `/upnp/event/IPControlService1`
- SCPD URL: `/IPControlService_1.xml`

The embedded SCPD is basically empty:

```xml
<scpd xmlns="urn:samsung.com:service-1-0">
  <specVersion><major>1</major><minor>0</minor></specVersion>
</scpd>
```

`IPControlServiceHelper::dispatchAction()` always returns `401 invalid action`.

Useful UPnP behavior found:

- evented state variable: `IPControlState`
- initial value: `RUNNING`
- `svSetIPControlState()` sends events for `IPControlState`

## Decompile Anchors

- HTTP parser/response:
  - `HTTPParser::parseHeaderCommon`
  - `HTTPParser::verifyHeader`
  - `HTTPParser::parseBody`
  - `HTTPServer::sendResponse`
- JSON-RPC:
  - `ServerManager::onReceiveCommand`
  - `ServiceManager::handleJsonRequest`
  - `ServiceManager::processCommand`
  - `JSONRPCParser::parse`
  - `JSONRPCParser::getAccessToken`
  - `JSONRPCParser::removeAccessToken`
- TV dispatch:
  - `DeviceManager::getDeviceType`
  - `DeviceFactory::getDeviceManager`
  - `TVManager::runCommand`
  - `MDEFHandler::_generateCommandMaps`
  - `MDEFHandler::getTypeForSetOp`
- UPnP:
  - `IPControlServiceHelper::dispatchAction`
  - `IPControlServiceHelper::svSetIPControlState`
