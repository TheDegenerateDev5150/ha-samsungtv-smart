# RPC / WebSocket Internals

Goal: explain message handlers, not just URL paths.

Sources:

- observed client behavior from Samsung TV integrations such as `ha-samsungtv-smart`
- TV binaries/packages:
  - `/usr/bin/msf-server`
  - `/usr/bin/remote-server`
  - `/opt/usr/apps/com.samsung.tv.remoteless/bin/remoteless`
  - `/usr/apps/com.samsung.tv.multiscreen/bin/MultiScreen.dll`
  - `/opt/usr/apps/com.samsung.tv.mde-framework/bin/mde-framework`
  - `/opt/usr/apps/org.tizen.art-app/bin/ArtApp.dll`
  - `/opt/usr/apps/org.tizen.art-app/bin/ArtDataManagement.dll`
  - `/usr/apps/org.tizen.ipcontrol/libipcontrol-http-server.so`
  - `/opt/usr/apps/com.samsung.tv.mde-framework/lib/libmde-protocol-ipcontrol.so`

## Big Picture

`msf-server` is the public MultiScreen/WebSocket daemon for 8001/8002.

`remote-server` is the backend/orchestrator. It does not directly bind 8001/8002 and its direct binds are Unix sockets:

- `/tmp/pcs`
- `/tmp/msf`

`msf-server` receives public WebSocket/REST messages, then calls local/internal backend commands in `remote-server` for app launch/install/ACL/etc.

`remoteless` is BLE/mobile remote. Not the 8001/8002/1516 protocol server.

`MultiScreen.dll` is MultiView/UI app glue. Not the 8001/8002/1516 protocol server.

## MSF WebSocket Envelope

The public WebSocket JSON shape is:

```json
{
  "id": "optional-client-id",
  "method": "ms.remote.control | ms.channel.emit | ms.application.get | ...",
  "params": {}
}
```

Embedded `msf-server` method/event strings:

- `ms.remote.control`
- `ms.voice.control`
- `ms.channel.emit`
- `ms.application.get`
- `ms.application.start`
- `ms.application.stop`
- `ms.application.install`
- `ms.webapplication.get`
- `ms.webapplication.start`
- `ms.webapplication.stop`
- `ms.gamepad.control`
- `ms.ocf.data`

Embedded channel lifecycle/error events:

- `ms.channel.connect`
- `ms.channel.ready`
- `ms.channel.clientConnect`
- `ms.channel.clientDisconnect`
- `ms.channel.disconnect`
- `ms.channel.timeOut`
- `ms.channel.unauthorized`
- `ms.error`

`ms.channel.emit` is the generic relay:

- expects `params.event`
- expects `params.to` when targeted; binary logs `params.to is not string!`
- routes/broadcasts to channel clients by id or `host`
- rejects custom events beginning with `ms.`: binary string says `Usage of \`ms.\` in custom event is not allowed.`

## Remote Control Channel

Public channel:

- `/api/v2/channels/samsung.remote.control`

Incoming method:

- `ms.remote.control`

Main dispatch key:

- `params.TypeOfRemote`

Embedded `TypeOfRemote` values:

- `SendRemoteKey`
- `SendInputString`
- `SendInputEnd`
- `CreateTouchDevice`
- `DestroyTouchDevice`
- `ProcessTouchDevice`
- `ProcessMouseDevice`
- `SendGamepadKey`
- `SendGamepadMove`

Known client payloads, matching binary strings:

```json
{
  "method": "ms.remote.control",
  "params": {
    "Cmd": "Click",
    "DataOfCmd": "KEY_HOME",
    "Option": "false",
    "TypeOfRemote": "SendRemoteKey"
  }
}
```

`Cmd` for `SendRemoteKey` maps to press type:

- `Click`
- `Press`
- `Release`

Implementation evidence:

- calls `remote_control_send_key_event`
- log string: `SendRemoteKey called keycode = %d, type = %d`
- includes a huge `KEY_*` string table: `KEY_HOME`, `KEY_POWER`, `KEY_HDMI`, `KEY_VOLUP`, `KEY_VOLDOWN`, `KEY_MULTI_VIEW`, `KEY_AMBIENT`, etc.

Text input payload:

```json
{
  "method": "ms.remote.control",
  "params": {
    "Cmd": "<base64 text>",
    "DataOfCmd": "base64",
    "TypeOfRemote": "SendInputString"
  }
}
```

Then:

```json
{
  "method": "ms.remote.control",
  "params": {
    "TypeOfRemote": "SendInputEnd"
  }
}
```

Implementation evidence:

- calls `remote_control_send_commit_string`
- has IME callbacks:
  - `remote_control_text_updated_callback_set`
  - `remote_control_entry_metadata_callback_set`
  - `remote_control_focus_in_callback_set`
  - `remote_control_focus_out_callback_set`

Mouse payload:

```json
{
  "method": "ms.remote.control",
  "params": {
    "Cmd": "Move",
    "Position": { "x": 100, "y": 100, "Time": "0" },
    "TypeOfRemote": "ProcessMouseDevice"
  }
}
```

Embedded mouse command strings:

- `Move`
- `LeftClick`
- `LeftPress`
- `LeftRelease`
- `RightClick`

Implementation evidence:

- calls `VirtualMouse_Send_Move`
- calls `VirtualMouse_Send_Button_Event`
- calls `autoinput_virtualmouse_generate_mouse_scroll`

## Server-Originated Remote Events

`msf-server` emits/understands these remote-state events:

- `ms.remote.touchEnable`
- `ms.remote.touchDisable`
- `ms.remote.imeStart`
- `ms.remote.imeUpdate`
- `ms.remote.imeDone`
- `ms.remote.imeEnd`
- `ms.remote.mbrlayout`
- `ms.remote.numberpad`
- `ms.voiceApp.hide`
- `ms.voiceApp.recording`
- `ms.voiceApp.processing`
- `ms.voiceApp.standby`
- `ed.edenTV.update`

Associated REST handlers in the same daemon update/broadcast these states:

- `/remoteControl/ime/`
- `/remoteControl/imeInput/`
- `/remoteControl/touchEnable/`
- `/remoteControl/voiceStatus/`
- `/remoteControl/edenMobile/`
- `/remoteControl/RcrToMobile/`
- `/remoteControl/virtualRemote/`
- `/remoteControl/mbrInfo/`

## Application Control

There are two layers.

Public WebSocket methods in `msf-server`:

- `ms.application.get`
- `ms.application.start`
- `ms.application.stop`
- `ms.application.install`

Public REST endpoints in `msf-server` are wrappers around the same idea:

- `GET /api/v2/applications/<id>`
- `POST /api/v2/applications/<id>`
- `DELETE /api/v2/applications/<id>`
- `PUT /api/v2/applications/<id>`

Internal backend commands passed to `remote-server` over `/tmp/msf`:

- `application.getApplication`
- `application.launchApplication`
- `application.stopApplication`
- `application.installApplication`
- `application.aclPairing`
- `application.getImeText`
- `application.setRemoteNumbers`
- `application.getCastingAppsInfo`
- `application.urlVerification`

`remote-server` contains matching backend handlers:

- `DoGetApplication`
- `DoLaunchApplication`
- `DoStopApplication`
- `DoInstallApplication`
- `DoACLPairing`
- `ParseJSON`
- `PacketParse`

So app control flow is:

```text
client -> msf-server public WS/REST -> /tmp/msf -> remote-server MSFServer::ParseJSON -> WAS/app launcher APIs
```

Home Assistant also sends this older Eden-style launch event:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "ed.apps.launch",
    "to": "host",
    "data": {
      "action_type": "DEEP_LINK | NATIVE_LAUNCH",
      "appId": "...",
      "metaTag": "..."
    }
  }
}
```

Note: literal `ed.apps.launch` was not found in the examined TV binaries. The lower-level application strings above are present. Treat `ed.apps.launch` as an observed client-facing Eden/MSF convention, not a direct string hit in `msf-server`.

## Installed App List

Home Assistant requests:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "ed.installedApp.get",
    "to": "host"
  }
}
```

Binary evidence:

- `remote-server` contains `CONNECT_INSTALLEDAPP`
- `msf-server`/`remote-server` contain the application backend commands above

But the literal `ed.installedApp.get` was not found in the examined TV binaries. This may be generated by Eden/app framework code or by another package.

## Gamepad Channel

Public channel:

- `/api/v2/channels/samsung.gamepad.control`

Embedded strings:

- `ms.gamepad.control`
- `gamepad_key`
- `gamepad_abs`
- `gamepad_left`
- `gamepad_right`
- `CreateGamepadDevice`
- `DestroyGamepadDevice`
- `/dev/uinput`

Implementation evidence:

- creates a virtual input/gamepad device
- logs gamepad key events
- writes via uinput

## Generic / Dynamic Channels

Hard-coded channel strings in `msf-server`:

- `/api/v2/channels/samsung.remote.control`
- `/api/v2/channels/samsung.gamepad.control`
- `/api/v2/channels/samsung.default.media.player`
- `/api/v2/channels/com.samsung.wallservice`
- `/api/v2/channels/com.samsung.tv.ambient`
- `/api/v2/channels/com.samsung.tv.ambient.contentapp`
- `/api/v2/channels/com.samsung.tv.mobilebff`
- `/api/v2/channels/com.samsung.edgeblending-service`
- `/api/v2/channels/com.samsung.virtualmicservice`

`/api/v2/channels/com.samsung.art-app` is used externally, but that literal was not found in `msf-server`. Explanation from the Art app decompile: `org.tizen.art-app` registers SmartView/MSF channel `com.samsung.art-app` itself, and `msf-server` provides generic channel routing.

## Art App Channel

Observed externally; the channel/event routing is confirmed by decompiling `/opt/usr/apps/org.tizen.art-app/bin/ArtDataManagement.dll`:

- channel: `/api/v2/channels/com.samsung.art-app`
- outer method: `ms.channel.emit`
- outer event: `art_app_request`
- response event: `d2d_service_message`
- inner payload is a JSON string in `params.data`

Request shape:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "art_app_request",
    "to": "host",
    "data": "{\"request\":\"get_artmode_status\",\"id\":\"...\",\"request_id\":\"...\"}"
  }
}
```

Client-observed inner requests include:

- `get_api_version`
- `api_version`
- `get_content_list`
- `get_current_artwork`
- `get_thumbnail_list`
- `get_thumbnail`
- `select_image`
- `get_artmode_status`
- `set_artmode_status`
- `change_favorite`
- `get_photo_filter_list`
- `set_photo_filter`
- `get_matte_list`
- `change_matte`
- `get_artmode_settings`
- `get_brightness`
- `set_brightness`
- `get_color_temperature`
- `set_color_temperature`
- `get_auto_rotation_status`
- `set_auto_rotation_status`
- `get_slideshow_status`
- `set_slideshow_status`
- `send_image`
- `delete_image_list`

Observed inner response/broadcast events:

- `artmode_status`
- `art_mode_changed`
- `go_to_standby`
- `wakeup`
- `brightness`
- `color_temperature`
- `favorite_changed`
- `error`

Important internal finding:

- the Art request strings are not in `msf-server`, `remote-server`, `remoteless`, or `MultiScreen.dll`
- the real inner request table is in `/opt/usr/apps/org.tizen.art-app/bin/ArtDataManagement.dll`
- `msf-server` owns the WebSocket transport; the Art app owns `art_app_request` parsing and `d2d_service_message` responses
- see `WEBSOCKET_DECOMPILED.md` for the full Art request/event catalogue

## 1516 JSON-RPC

Full decompile-backed catalogue: `IPCONTROL_DECOMPILED.md`.

Short version:

- live process: `owner ... /opt/usr/apps/com.samsung.tv.mde-framework/bin/mde-framework`
- package: `com.samsung.tv.mde-framework`, `Onboot: 1`, `Autorestart: 1`
- library chain:
  - `mde-framework`
  - links `libmde-protocol-ipcontrol.so`
  - dlopens `/usr/apps/org.tizen.ipcontrol/libipcontrol-http-server.so`
- port logic: `GetTVYear() < 20 ? 1515 : 1516`
- this TV: `0.0.0.0:1516`
- banner: `Server: Samsung IP Control Server/1.0`
- TLS cert subject/issuer: `CN = Samsung IP Control G2`

HTTP transport:

- POST only
- HTTP/1.0 or HTTP/1.1 only
- no URL route dispatch found; target path is effectively ignored
- required headers: `Content-Type: application/json`, `Accept: application/json`, `Host`, `Content-Length`
- chunked POST is explicitly unsupported
- no WebSocket implementation in this server

JSON-RPC:

- body must parse as JSON
- `jsonrpc` must be `"2.0"`
- `createAccessToken` is the token bootstrap method
- every other method requires `params.AccessToken`
- token auth is tied to peer MAC/auth-list checks
- set-vs-get is decided by params: only `AccessToken` means get; any extra param means set

Normal-TV method maps from decompile:

- open/expert map: `volumeUpDnControl`, `channelUpDnControl`, `muteControl`, `powerControl`, `artModeControl`, `directAccessControl`, `firstScreenAppControl`, `remoteKeyControl`, `getVideoStates`, `getTVStates`, `multiviewControl`, `displayRotatorControl`, `getDeviceInformation`, plus expert-picture controls such as `backlightControl`, `peakBrightnessControl`, `colorSpace.ColorControl`, `gameModeControl`, etc.
- none-ambient map: `directVolumeControl`, `inputSourceControl`, `directChannelControl`, `pictureModeControl`, `pictureSizeControl`, `soundModeControl`, `speakerSelectControl`, `externalSpeakerControl`, `USBSourceControl`, `brightnessControl`, `contrastControl`, `sharpnessControl`, `colorControl`, `tintControl`
- wall map: `ambientControl`, `getBoxStates`, `getCabinetGroupIds`, `getCabinetStates`
- HTV-only and AV/soundbar-only maps also exist; see the dedicated note.

Important corrections:

- `RVUSourceControl` and `ambientModeControl` are not exact strings in this library.
- `ambientControl` is present.
- `getAccessToken` and `removeAccessToken` are parser helpers, not public JSON-RPC methods.
- same module has UPnP description/event code, but `IPControlServiceHelper::dispatchAction()` always returns invalid action; it only event-publishes `IPControlState`.
