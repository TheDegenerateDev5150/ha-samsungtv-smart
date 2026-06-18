# TV Port Owners / Internal Behavior

TV binaries examined:

- `/usr/bin/msf-server`
- `/usr/bin/remote-server`
- `/opt/usr/apps/com.samsung.tv.remoteless/bin/remoteless`
- `/usr/apps/com.samsung.tv.multiscreen/bin/MultiScreen.dll`

Live state seen on TV:

- `owner 4894 /usr/bin/msf-server`
- `owner 2006 /usr/bin/remote-server`
- `owner 747 /opt/usr/apps/com.samsung.tv.remoteless/bin/remoteless`
- `owner 2316 /usr/apps/com.samsung.tv.multiscreen/bin/MultiScreen.dll ...`
- `/proc/net/tcp`: `0.0.0.0:8001`, `0.0.0.0:8002`, `0.0.0.0:1516`
- no `1515` listener

`sdk` cannot read `/proc/<owner-pid>/fd` or `/proc/<owner-pid>/maps`; `netstat -p` also hides PIDs. So listener inode -> PID is blocked without root or an owner-UID helper.

## 8001 / 8002

Owner: `/usr/bin/msf-server`.

Why:

- service unit runs `/usr/bin/msf-server` as `owner`, after `remote-server.service`
- binary imports `libwebsockets.so.19`
- strings contain `8001`, `8002`, and `can't create vhost for '8002' port`
- TLS files: `/usr/share/msf-server/certificates/server_crt.pem`, `server_key.pem`, `ca_crt.pem`
- mDNS advertises `:8001/api/v2/` and `:8001/ms/1.0/`

What it exposes:

- REST:
  - `/api/v2/`
  - `/ms/1.0/device/info/update`
  - `/ms/1.0/device/discovery`
  - `/api/v2/applications/11091000000`
  - `/api/v2/applications/`
  - `/api/v2/webapplication/`
  - `/api/v2/webapplication/data`
  - `/remoteControl/`, `/remoteControl/ime/`, `/remoteControl/touchEnable/`, `/remoteControl/voiceStatus/`, `/remoteControl/imeInput/`, etc.
- WebSocket:
  - `/api/v2/channels/samsung.remote.control`
  - `/api/v2/channels/samsung.gamepad.control`
  - `/api/v2/channels/samsung.default.media.player`
- auth/pairing:
  - `token`, `token_check`, `CheckACLPairing`, `ms.channel.unauthorized`
- actions:
  - `remote_control_send_key_event`
  - `remote_control_send_commit_string`
  - `VirtualKey_Send_KeyCode`
  - `VirtualMouse_Send_Move`
  - gamepad via `/dev/uinput`
  - app launch/install/stop through `application.*` commands

## remote-server

Owner: `/usr/bin/remote-server`.

It is the backend/orchestrator, not the direct 8001/8002 server.

Direct binds found in disassembly:

- `socket(AF_UNIX, SOCK_STREAM, 0)` + `bind()` + `listen()` on `/tmp/pcs`
- `socket(AF_UNIX, SOCK_STREAM, 0)` + `bind()` + `listen()` on `/tmp/msf`

No direct TCP bind for 1516 was found in this executable.

What it does:

- DIAL/app control:
  - registers WebConv services `/ws/apps` and `/ws/app`
  - handles app list, app info, app launch, app stop, app install
  - uses WAS launcher APIs
- UPnP/RCR:
  - calls `asf_upnp::framework_core::ConfigureServers(7678, 1900, 0, false)`
  - embeds `Samsung DTV RCR` XML
  - embeds `/RCR/control/dial`, `/RCR/event/dial`
  - embeds UPnP action `SendKeyCode`
- pairing/auth:
  - `REMOTE_ACL_LIST`, `DEVICE_AUTH_LIST`
  - token read/write/check
  - RDM access UX callbacks
- bridge to msf:
  - local socket `/tmp/msf`
  - calls `http://127.0.0.1:8001/ms/1.0/device/info/update`
  - calls `http://127.0.0.1:8001/remoteControl/...`

## remoteless

Owner: `/opt/usr/apps/com.samsung.tv.remoteless/bin/remoteless`.

Not a TCP server candidate.

Why:

- imports Bluetooth/GATT, `remote_input_*`, `VirtualKey_*`, `VirtualMouse_*`
- no useful socket/listen/bind/http server strings
- service is gated by Bluetooth mobile remote feature flags

What it does:

- BLE mobile remote scanning/register/power-on
- iOS/Android direct power control
- uses `/opt/usr/home/owner/apps_rw/com.samsung.tv.remoteless/data/mobile_registered`
- sends key/text/mouse through `remote_input_*` and `autoinput`

## MultiScreen.dll

Owner: `com.samsung.tv.multiscreen` app.

Not a TCP server candidate from pulled metadata/strings.

It is a .NET in-house app using CoBA/ScreenOnScreen/TVService/Bixby/Tizen APIs for MultiView/UI state.

## 1516

Known:

- listener exists: `0.0.0.0:1516`, UID `5001`/`owner`
- `1515` is absent
- TV-shell request to `https://<TV_LAN_IP>:1516/` returns `Server: Samsung IP Control Server/1.0`
- TLS cert subject/issuer is `CN = Samsung IP Control G2`

Owner:

- process: `owner 4268 /opt/usr/apps/com.samsung.tv.mde-framework/bin/mde-framework`
- package: `com.samsung.tv.mde-framework`
- component: `svcapp`
- manifest DB says `Onboot: 1`, `Autorestart: 1`

Implementation:

- `mde-framework` directly links `libmde-protocol-ipcontrol.so`
- `libmde-protocol-ipcontrol.so` contains `CreateIPControlPlugin`, `IPControlCore`, `ServerManager`, `JSONRPCParser`, the JSON-RPC method table, and access-token handling
- `libmde-protocol-ipcontrol.so` loads `/usr/apps/org.tizen.ipcontrol/libipcontrol-http-server.so`
- `libipcontrol-http-server.so` implements the Boost.Asio/OpenSSL HTTPS listener and contains the exact `Samsung IP Control Server/1.0` banner

Adjacent:

- `sddp.service` runs `/usr/apps/org.tizen.sddp/bin/SDDP`, gated by the same `convergence.ipcontrol.service_available` feature flag, but it is discovery/advertising, not the HTTPS JSON-RPC server
- `remote-server` directly binds only `/tmp/pcs` and `/tmp/msf`
- `remote-server` UPnP framework config is `7678` + `1900`, not `1516`
