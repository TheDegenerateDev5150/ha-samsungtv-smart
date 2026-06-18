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
| `powerControl` | `power` string | accepts `powerOn`, `powerOff`, `reboot`, `force-reboot` |
| `volumeUpDnControl` | `control` string | expected `volumeUp` or `volumeDn`; helper accepts any key alias below |
| `channelUpDnControl` | `control` string | expected `channelUp` or `channelDn`; helper accepts any key alias below |
| `remoteKeyControl` | `remoteKey` string | helper maps alias to Samsung `KEY_*` and sends `pressAndRelease` |
| `directVolumeControl` | `volume` int | direct absolute volume |
| `muteControl` | `mute` string | `muteOn` or `muteOff`; `getTVStates` is the clean mute getter |
| `soundModeControl` | `soundMode` string | value passed through |
| `speakerSelectControl` | `speakerSelect` string | public values are `Internal`, `External`, `AudioOut/Optical`; helper rewrites to internal values |
| `externalSpeakerControl` | `deviceName` string, `deviceId` string | builds internal JSON with `id`/name |
| `inputSourceControl` | `inputSource` string | value passed through; TV is normalized internally |
| `USBSourceControl` | `deviceName` string, `deviceId` string | helper sends `deviceId` as internal `additionalData` |
| `directChannelControl` | `atvDtv` string, `airCable` string, `channelNum` string | converted internally to `channelType`, `RFtype`, `channelNumber` |
| `pictureModeControl` | `pictureMode` string | value passed through |
| `pictureSizeControl` | `pictureSize` string | value passed through |
| `contrastControl` | `contrast` int | |
| `brightnessControl` | `brightness` int | |
| `sharpnessControl` | `sharpness` int | |
| `colorControl` | `color` int | |
| `tintControl` | `tint` int | |
| `artModeControl` | `artMode` string | `artModeOn` is special: emits `/v2/powerValue` with `{"mode":"ambient"}` |
| `directAccessControl` | `applicationName` string | mapped to app id; known built-ins include `youTube`, `netflix`, `amazon` |
| `firstScreenAppControl` | `applicationName` string | no extra params queries first-screen apps/state |
| `multiviewControl` | `multiviewMode` string | no extra params queries supported/current modes |
| `displayRotatorControl` | `orientation` string | accepts `portrait` or `landscape`; result uses `Portrait`/`Landscape` |
| `ambientControl` | `ambientId` string | wall/microLED map |
| `getCabinetStates` | `groupId` int | wall/microLED map |
| `getBoxStates` | none | get-only |
| `getCabinetGroupIds` | none | get-only |
| `getVideoStates` | none | get-only; result has `contrast`, `sharpness`, `brightness`, `color` |
| `getTVStates` | none | get-only; result is postprocessed TV state, including source/mute fields when present |
| `getDeviceInformation` | none | get-only; result includes `modelID`, `serialNumber`, `FWVersion` |

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
| `powerControl` | `power` string | |
| `remoteKeyControl` | `remoteKey` string | |
| `inputSelectControl` | `inputSource` string | |
| `soundModeControl` | `soundMode` string | |
| `volumeControl` | `volume` int | |
| `muteControl` | `mute` bool | AV path uses bool, not normal-TV `muteOn`/`muteOff` |
| `getVolume` | none | get-only, returns `volume` |
| `getMute` | none | get-only, returns `mute` |
| `getCodec` | none | get-only, returns `codec` |
| `getIdentifier` | none | get-only, returns `identifier` |
| `getIPControlState` | none | get-only, returns `ipcontrolState` |

HTV params are not decoded per method in this library. `HTVMDEFHandler` forwards
the full params JSON as `setCommand` when any non-`AccessToken` member exists,
otherwise as `getCommand`; the external HTV service owns the method-specific
schema.

## QN55LS03FAFXZA Empirical Probe

Probe evidence:

- Generated: `2026-06-18T03:10:00Z`
- Target: `192.168.86.68:1516`
- Mode: unsafe (`--unsafe=true`, `--explore=true`)
- Summary: ✅ `30`, ⚠️ `28`, ❌ `37`
- Range/alternate restore calls: `14/14` succeeded.
- Disruptive app/channel/remote actions were executed after the non-destructive getter/setter/range probes.

Observed identity:

```json
{
  "getDeviceInformation": {
    "modelID": "25_PTM_FTV",
    "FWVersion": "T-PTMFAKUC-0090-1296.8"
  },
  "getTVStates": {
    "inputSource": "TV",
    "mute": "muteOff",
    "pictureMode": "Standard",
    "pictureSize": "16:9",
    "soundMode": "Standard",
    "speakerSelect": "internal",
    "volume": 3
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

Legend: ✅ works, ⚠️ partial/params rejected/server error, ❌ failed or method not found. `n/a` means no method-specific setter form is documented.


### Group: auth

| Method | Getter | Getter Results | Setter | Setter Params | Notes |
| --- | --- | --- | --- | --- | --- |
| `createAccessToken` | ✅ | `{"AccessToken":"..."}` | n/a | n/a | Pairing only |


### Group: av/soundbar

| Method | Getter | Getter Results | Setter | Setter Params | Notes |
| --- | --- | --- | --- | --- | --- |
| `getCodec` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | n/a | n/a | Soundbar-only get |
| `getIPControlState` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | n/a | n/a | Soundbar-only get |
| `getIdentifier` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | n/a | n/a | Soundbar-only get |
| `getMute` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | n/a | n/a | Soundbar-only get |
| `getVolume` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | n/a | n/a | Soundbar-only get |
| `inputSelectControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"inputSource":"TV"}` | Soundbar-only on this TV |
| `volumeControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"volume":3}` | Soundbar-only on this TV; no range probing |


### Group: htv

| Method | Getter | Getter Results | Setter | Setter Params | Notes |
| --- | --- | --- | --- | --- | --- |
| `HTVFactoryLockControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `HTVRoomStatusControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `duplicateHTVConfigControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `forwardMessage` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `getHTVInformation` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `getHTVNetworkInformation` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `getSoftAPSecurityKey` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `setHTVTime` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `showHTVNotification` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `softAPSSIDControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `softAPSignalLevelControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `softAPStatusControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `softAPWiFiChannelControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `tvPlusDisable` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |
| `updateFirmware` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"probe":true}` | Expected to fail on consumer Frame |


### Group: normal/expert-picture

| Method | Getter | Getter Results | Setter | Setter Params | Notes |
| --- | --- | --- | --- | --- | --- |
| `AMP.LEDClearMotionControl` | ✅ | `{"AMP.LEDClearMotion":"Off"}` | ❌ -32002 | `{"AMP.LEDClearMotion":"Off"}` |  |
| `AMP.blurReductionControl` | ✅ | `{"AMP.blurReduction":10}` | ❌ -32002 | `{"AMP.blurReduction":10}` |  |
| `AMP.judderReductionControl` | ✅ | `{"AMP.judderReduction":10}` | ❌ -32002 | `{"AMP.judderReduction":10}` |  |
| `HDRToneMappingControl` | ✅ | `{"HDRToneMapping":"0"}` | ❌ -32002 | `{"HDRToneMapping":"0"}` |  |
| `RGBOnlyModeControl` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"RGBOnlyMode":"Off"}` |  |
| `WB20P.BlueControl` | ✅ | `{"WB20P.Blue":0}` | ❌ -32002 | `{"WB20P.Blue":0}` |  |
| `WB20P.GreenControl` | ✅ | `{"WB20P.Green":0}` | ❌ -32002 | `{"WB20P.Green":0}` |  |
| `WB20P.IntervalControl` | ✅ | `{"WB20P.Interval":"5%"}` | ❌ -32002 | `{"WB20P.Interval":"5%"}` |  |
| `WB20P.RedControl` | ✅ | `{"WB20P.Red":0}` | ❌ -32002 | `{"WB20P.Red":0}` |  |
| `WB20PointModeControl` | ✅ | `{"WB20PointMode":"Off"}` | ✅ | `{"WB20PointMode":"Off"}` | WB20PointMode alternate probe {"On":"✅"} restore=✅ |
| `WB2PointControl` | ✅ | `{"B-Gain":0,"B-Offset":0,"G-Gain":0,"G-Offset":0,"R-Gain":0,"R-Offset":0}` | ✅ | `{"B-Gain":0,"B-Offset":0,"G-Gain":0,"G-Offset":0,"R-Gain":0,"R-Offset":0}` | Special WB2Point payload; same-value map when getter works |
| `applyPictureSettingsControl` | ✅ | `{"applyPictureSettings":"AllSources"}` | ✅ | `{"applyPictureSettings":"AllSources"}` |  |
| `autoHDRRemasteringControl` | ✅ | `{"autoHDRRemastering":"Off"}` | ✅ | `{"autoHDRRemastering":"Off"}` | autoHDRRemastering alternate probe {"On":"✅"} restore=✅ |
| `autoMotionPlusControl` | ✅ | `{"autoMotionPlus":"Auto"}` | ✅ | `{"autoMotionPlus":"Auto"}` |  |
| `autoPowerOffControl` | ✅ | `{"autoPowerOff":"Off"}` | ✅ | `{"autoPowerOff":"Off"}` | autoPowerOff alternate probe {"On":"❌ -32002"} restore=✅ |
| `autoPowerSavingControl` | ✅ | `{"autoPowerSaving":"Off"}` | ✅ | `{"autoPowerSaving":"Off"}` | autoPowerSaving alternate probe {"On":"✅"} restore=✅ |
| `backlightControl` | ✅ | `{"backlight":25}` | ✅ | `{"backlight":25}` | backlight probe accepted 0..50; accepted=[0,1,10,25,50] rejected=[-101,-100,-51,-50,-26,-25,-11,-10,-1,51,100,101] restore=✅ |
| `brightnessOptimizationControl` | ✅ | `{"brightnessOptimization":"Off"}` | ✅ | `{"brightnessOptimization":"Off"}` | brightnessOptimization alternate probe {"On":"✅"} restore=✅ |
| `colorBoosterControl` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"colorBooster":"Off"}` |  |
| `colorSpace.BlueControl` | ✅ | `{"colorSpace.Blue":50}` | ❌ -32002 | `{"colorSpace.Blue":50}` |  |
| `colorSpace.ColorAdjustmentPointControl` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"colorSpace.ColorAdjustmentPoint":"Off"}` |  |
| `colorSpace.ColorControl` | ✅ | `{"colorSpace.Color":"Red"}` | ❌ -32002 | `{"colorSpace.Color":"Red"}` |  |
| `colorSpace.GreenControl` | ✅ | `{"colorSpace.Green":53}` | ❌ -32002 | `{"colorSpace.Green":53}` |  |
| `colorSpace.RedControl` | ✅ | `{"colorSpace.Red":40}` | ❌ -32002 | `{"colorSpace.Red":40}` |  |
| `colorSpaceControl` | ✅ | `{"colorSpace":"Native"}` | ✅ | `{"colorSpace":"Native"}` |  |
| `colorSpaceGamutControl` | ✅ | `{"colorSpaceGamut":"BT.709"}` | ❌ -32002 | `{"colorSpaceGamut":"BT.709"}` |  |
| `colorToneControl` | ✅ | `{"colorTone":"Standard"}` | ✅ | `{"colorTone":"Standard"}` |  |
| `contrastEnhancerControl` | ✅ | `{"contrastEnhancer":"High"}` | ✅ | `{"contrastEnhancer":"High"}` |  |
| `digitalCleanViewControl` | ✅ | `{"digitalCleanView":"Standard"}` | ❌ -32002 | `{"digitalCleanView":"Standard"}` |  |
| `energySavingSolutionControl` | ✅ | `{"energySavingSolution":"Off"}` | ✅ | `{"energySavingSolution":"Off"}` | energySavingSolution alternate probe {"On":"✅"} restore=✅ |
| `filmModeControl` | ✅ | `{"filmMode":"Off"}` | ❌ -32002 | `{"filmMode":"Off"}` |  |
| `gameModeControl` | ✅ | `{"gameMode":"Off"}` | ❌ -32002 | `{"gameMode":"Off"}` |  |
| `gamma.BT1886Control` | ✅ | `{"gamma.BT1886":0}` | ✅ | `{"gamma.BT1886":0}` | gamma.BT1886 probe accepted -1..1; accepted=[-1,0,1] rejected=[-101,-100,-51,-50,-26,-25,-11,-10,10,25,50,51,100,101] restore=✅ |
| `gamma.HLGControl` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"gamma.HLG":0}` |  |
| `gamma.ST2084Control` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"gamma.ST2084":0}` |  |
| `gammaModeControl` | ✅ | `{"gammaMode":"BT.1886"}` | ✅ | `{"gammaMode":"BT.1886"}` |  |
| `localDimmingControl` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"localDimming":"Off"}` |  |
| `motionLightingControl` | ✅ | `{"motionLighting":"Off"}` | ✅ | `{"motionLighting":"Off"}` | motionLighting alternate probe {"On":"✅"} restore=✅ |
| `peakBrightnessControl` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"peakBrightness":"Off"}` |  |
| `pictureCalibrationModeControl` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"pictureCalibrationMode":"Off"}` |  |
| `pixelShiftMenuControl` | ❌ -32002 | `{"error":{"code":-32002,"message":"Server error","type":"jsonrpc"}}` | ❌ -32002 | `{"pixelShiftMenu":"Off"}` |  |


### Group: normal/none-ambient

| Method | Getter | Getter Results | Setter | Setter Params | Notes |
| --- | --- | --- | --- | --- | --- |
| `USBSourceControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"deviceId":"__probe__","deviceName":"__probe__"}` | Real set needs USB deviceName/deviceId |
| `brightnessControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"brightness":0}` |  |
| `colorControl` | ✅ | `{"color":15}` | ✅ | `{"color":15}` | color probe accepted 0..50; accepted=[0,1,10,15,25,50] rejected=[-101,-100,-51,-50,-26,-25,-11,-10,-1,51,100,101] restore=✅ |
| `contrastControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"contrast":50}` |  |
| `directChannelControl` | ✅ | `{"airCable":"cable","atvDtv":"tvplus","channelNum":"1001"}` | ❌ -32002 | `{"airCable":"AIR","atvDtv":"DTV","channelNum":"1"}` | Changes channel when set works |
| `directVolumeControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"volume":3}` | No range probing; avoid loud volume jumps |
| `externalSpeakerControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"deviceId":"__probe__","deviceName":"__probe__"}` | Real set needs deviceName/deviceId from speaker list |
| `inputSourceControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"inputSource":"TV"}` |  |
| `pictureModeControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"pictureMode":"Standard"}` |  |
| `pictureSizeControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"pictureSize":"16:9"}` |  |
| `sharpnessControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"sharpness":10}` |  |
| `soundModeControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"soundMode":"Standard"}` |  |
| `speakerSelectControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"speakerSelect":"internal"}` |  |
| `tintControl` | ✅ | `{"tint":0}` | ✅ | `{"tint":0}` | tint probe accepted -11..10; accepted=[-11,-10,-1,0,1,10] rejected=[-101,-100,-51,-50,-26,-25,25,50,51,100,101] restore=✅ |


### Group: normal/open

| Method | Getter | Getter Results | Setter | Setter Params | Notes |
| --- | --- | --- | --- | --- | --- |
| `artModeControl` | ✅ | `{"artMode":"artModeOff"}` | ✅ | `{"artMode":"artModeOff"}` | artMode alternate probe {"artModeOn":"✅"} restore=✅ |
| `channelUpDnControl` | ⚠️ -32602 | `{"error":{"code":-32602,"message":"Invalid params","type":"jsonrpc"}}` | ✅ | `{"control":"channelUp"}` | Remote-key style |
| `directAccessControl` | ✅ | `{"applicationName":"unknown"}` | ✅ | `{"applicationName":"youTube"}` | Launches app when set works |
| `displayRotatorControl` | ✅ | `{"orientation":"Landscape"}` | ✅ | `{"orientation":"landscape"}` | orientation alternate probe {"portrait":"✅"} restore=✅ |
| `firstScreenAppControl` | ✅ | `[{"applicationName":"Apple TV"},{"applicationName":"Bixby"},{"applicationName":"Disney+"},{"applicationName":"ESPN"},{"applicationName":"Hulu"},{"applicationName":"Internet"},{"applicationName":"Netflix"},{"applicationName":"Peacock TV"},{"applicationName":"Plex - Free Movies ＆ TV"},{"applicationName":"Prime Video"},{"applicationName":"Sling TV"},{"applicationName":"SmartThings"},{"applicationName":"Spotify - Music and Podcasts"},{"applicationName":"Vision AI Companion"},{"applicationName":"YouTube"},{"applicationName":"YouTube TV"}]` | ❌ -32002 | `{"applicationName":"youTube"}` | May launch/select app |
| `getDeviceInformation` | ✅ | `{"FWVersion":"T-PTMFAKUC-0090-1296.8","modelID":"25_PTM_FTV","serialNumber":"<redacted>"}` | n/a | n/a | get-only |
| `getTVStates` | ✅ | `{"inputSource":"TV","mute":"muteOff","pictureMode":"Standard","pictureSize":"16:9","soundMode":"Standard","speakerSelect":"internal","volume":3}` | n/a | n/a | get-only |
| `getVideoStates` | ✅ | `{"brightness":0,"color":15,"contrast":50,"sharpness":10,"tint":0}` | n/a | n/a | get-only |
| `multiviewControl` | ✅ | `[]` | ❌ -32002 | `{"multiviewMode":"Off"}` |  |
| `muteControl` | ✅ | `{"mute":"muteOff"}` | ✅ | `{"mute":"muteOff"}` | mute alternate probe {"muteOn":"✅"} restore=✅ |
| `powerControl` | ✅ | `{"power":"powerOn"}` | ✅ | `{"power":"powerOn"}` | Only tests powerOn, not powerOff/reboot |
| `remoteKeyControl` | ⚠️ -32602 | `{"error":{"code":-32602,"message":"Invalid params","type":"jsonrpc"}}` | ✅ | `{"remoteKey":"return"}` | Remote-key style |
| `volumeUpDnControl` | ⚠️ -32602 | `{"error":{"code":-32602,"message":"Invalid params","type":"jsonrpc"}}` | ✅ | `{"control":"volumeUp"}` | Remote-key style |


### Group: normal/wall

| Method | Getter | Getter Results | Setter | Setter Params | Notes |
| --- | --- | --- | --- | --- | --- |
| `ambientControl` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"ambientId":"Off"}` |  |
| `getBoxStates` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | n/a | n/a | get-only |
| `getCabinetGroupIds` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | n/a | n/a | get-only |
| `getCabinetStates` | ❌ -32601 | `{"error":{"code":-32601,"message":"Method not found","type":"jsonrpc"}}` | ❌ -32601 | `{"groupId":0}` | Getter that requires groupId |


Response shape:

```json
{"jsonrpc":"2.0","id":"1","result":{...}}
```

or:

```json
{"jsonrpc":"2.0","id":"1","error":{"code":-32601,"message":"Method not found"}}
```

Compiled error templates:

- `-32700 Parse error`
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

- `volumeUpDnControl`
- `channelUpDnControl`
- `muteControl`
- `powerControl`
- `artModeControl`
- `directAccessControl`
- `firstScreenAppControl`
- `remoteKeyControl`
- `getVideoStates`
- `getTVStates`
- `multiviewControl`
- `displayRotatorControl`
- `getDeviceInformation`

Expert-picture entries in open map:

- `pictureCalibrationModeControl`
- `backlightControl`
- `digitalCleanViewControl`
- `autoMotionPlusControl`
- `AMP.blurReductionControl`
- `AMP.judderReductionControl`
- `AMP.LEDClearMotionControl`
- `localDimmingControl`
- `filmModeControl`
- `contrastEnhancerControl`
- `colorToneControl`
- `WB2PointControl`
- `WB20PointModeControl`
- `WB20P.IntervalControl`
- `WB20P.RedControl`
- `WB20P.GreenControl`
- `WB20P.BlueControl`
- `gammaModeControl`
- `gamma.BT1886Control`
- `gamma.ST2084Control`
- `gamma.HLGControl`
- `RGBOnlyModeControl`
- `colorSpaceControl`
- `colorSpace.ColorControl`
- `colorSpace.ColorAdjustmentPointControl`
- `colorSpace.RedControl`
- `colorSpace.GreenControl`
- `colorSpace.BlueControl`
- `HDRToneMappingControl`
- `colorSpaceGamutControl`
- `peakBrightnessControl`
- `colorBoosterControl`
- `autoHDRRemasteringControl`
- `brightnessOptimizationControl`
- `energySavingSolutionControl`
- `gameModeControl`
- `applyPictureSettingsControl`
- `motionLightingControl`
- `autoPowerSavingControl`
- `autoPowerOffControl`
- `pixelShiftMenuControl`

None-ambient map:

- `directVolumeControl`
- `inputSourceControl`
- `directChannelControl`
- `pictureModeControl`
- `pictureSizeControl`
- `soundModeControl`
- `speakerSelectControl`
- `externalSpeakerControl`
- `USBSourceControl`
- `brightnessControl`
- `contrastControl`
- `sharpnessControl`
- `colorControl`
- `tintControl`

Wall map:

- `ambientControl`
- `getBoxStates`
- `getCabinetGroupIds`
- `getCabinetStates`

Not present as exact strings in this pulled library:

- `RVUSourceControl`
- `ambientModeControl`

## HTV JSON-RPC Methods

HTV-specific map:

- `softAPStatusControl`
- `softAPSSIDControl`
- `getSoftAPSecurityKey`
- `softAPWiFiChannelControl`
- `softAPSignalLevelControl`
- `getHTVNetworkInformation`
- `getHTVInformation`
- `duplicateHTVConfigControl`
- `HTVFactoryLockControl`
- `HTVRoomStatusControl`
- `setHTVTime`
- `showHTVNotification`
- `updateFirmware`
- `forwardMessage`
- `tvPlusDisable`

## AV/Soundbar JSON-RPC Methods

Only selected when `SystemInfoUtil::IsSoundbar()` makes device type `AV`.

AV property map:

- `powerControl`
- `remoteKeyControl`
- `inputSelectControl`
- `soundModeControl`
- `volumeControl`
- `getVolume`
- `muteControl`
- `getMute`
- `getCodec`
- `getIdentifier`
- `getIPControlState`

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
