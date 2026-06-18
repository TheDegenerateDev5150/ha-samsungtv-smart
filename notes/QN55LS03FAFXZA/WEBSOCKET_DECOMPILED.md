# Samsung 8001/8002 WebSocket Decompile

Device: `QN55LS03FAFXZA`

Samsung support: https://www.samsung.com/us/support/downloads/?model=N0003009&modelCode=QN55LS03FAFXZA

Documented: `2026-06-18`

Firmware: `T-PTMFAKUC-0090-1296.8`

Tizen: `9.0.0`

Linux: `5.4.261 armv7l`

## Sources

- `/usr/bin/msf-server`
- `/usr/bin/remote-server`
- `/opt/usr/apps/org.tizen.art-app/tizen-manifest.xml`
- `/opt/usr/apps/org.tizen.art-app/bin/ArtApp.dll`
- `/opt/usr/apps/org.tizen.art-app/bin/ArtDataManagement.dll`
- `/opt/usr/apps/com.samsung.tv.coba.art/tizen-manifest.xml`
- `/opt/usr/apps/com.samsung.tv.home.art/tizen-manifest.xml`
- `/usr/apps/com.samsung.tv.wizard.art/tizen-manifest.xml`

## Port Owners

`8001` and `8002` are served by `/usr/bin/msf-server`.

`msf-server` is the public HTTP/WebSocket daemon. `remote-server` is the local backend bridge for remote/app-control operations over `/tmp/msf`; it does not directly bind `8001`/`8002`.

`8001` is the normal HTTP/WebSocket endpoint. `8002` is the TLS WebSocket endpoint using the same MSF channel model.

## Generic MSF WebSocket

Connect to:

```text
ws://<tv>:8001/api/v2/channels/<channel>
wss://<tv>:8002/api/v2/channels/<channel>
```

Common outer request:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "some_event",
    "to": "host",
    "data": "payload"
  }
}
```

`msf-server` rejects custom events beginning with `ms.`. `params.event` must be a string. `params.to` must be a string when present.

### Generic Methods

| Method | Params | Backend / notes |
|---|---|---|
| `ms.channel.emit` | `event`, optional `to`, optional `data` | Generic channel event relay. Used by Art app. |
| `ms.remote.control` | `TypeOfRemote`, `Cmd`, `DataOfCmd`, `Option`, optional `Position` | Virtual remote input. |
| `ms.voice.control` | voice payload | Voice state/control path; strings show `ms.voiceApp.*` events. |
| `ms.gamepad.control` | gamepad key/abs/move data | Uses `/dev/uinput`; creates/destroys virtual gamepad. |
| `ms.application.get` | app id / app query | Delegates to `remote-server` command `application.getApplication`. |
| `ms.application.start` | app id, optional launch/deeplink data | Delegates to `application.launchApplication`. |
| `ms.application.stop` | app id | Delegates to `application.stopApplication`. |
| `ms.application.install` | app id / install metadata | Delegates to `application.installApplication`. |
| `ms.webapplication.get` | web app id/query | Web app variant of application get. |
| `ms.webapplication.start` | web app id/launch data | Web app launch. |
| `ms.webapplication.stop` | web app id | Web app stop. |
| `ms.ocf.data` | OCF data payload | Generic OCF bridge. |
| `channel.ping` / `ms:channel.ping` | none seen | Channel keepalive/ping strings. |

### Generic Channels

Hard-coded public channel strings in `msf-server`:

| Channel |
|---|
| `samsung.remote.control` |
| `samsung.gamepad.control` |
| `samsung.default.media.player` |
| `com.samsung.wallservice` |
| `com.samsung.tv.ambient` |
| `com.samsung.tv.ambient.contentapp` |
| `com.samsung.tv.mobilebff` |
| `com.samsung.edgeblending-service` |
| `com.samsung.virtualmicservice` |

`com.samsung.art-app` is registered by the Art app through the SmartView/MSF local service API, not hard-coded in `msf-server`.

### Generic Events

| Event | Direction | Notes |
|---|---|---|
| `ms.channel.connect` | server -> client | Channel connect. |
| `ms.channel.ready` | server -> client | Host/channel ready. |
| `ms.channel.clientConnect` | server -> client | Another client joined. |
| `ms.channel.clientDisconnect` | server -> client | Client left. |
| `ms.channel.disconnect` | server -> client | Channel disconnect. |
| `ms.channel.timeOut` | server -> client | Channel timeout. |
| `ms.channel.unauthorized` | server -> client | Pairing/auth failure. |
| `ms.error` | server -> client | Generic MSF error. |
| `ms.remote.touchEnable` / `ms.remote.touchDisable` | server -> client | Touch remote state. |
| `ms.remote.imeStart` / `ms.remote.imeUpdate` / `ms.remote.imeDone` / `ms.remote.imeEnd` | server -> client | IME text input state. |
| `ms.remote.mbrlayout` / `ms.remote.numberpad` | server -> client | Remote UI overlays. |
| `ms.voiceApp.hide` / `recording` / `processing` / `standby` | server -> client | Voice UI state. |
| `ed.edenTV.update` | server -> client | Eden/Home update event. |

### Remote Control Params

`ms.remote.control` dispatches mostly by `params.TypeOfRemote`:

| `TypeOfRemote` | Params / values | Effect |
|---|---|---|
| `SendRemoteKey` | `Cmd`: `Click`, `Press`, `Release`; `DataOfCmd`: `KEY_*`; `Option`: usually `"false"` | Calls `remote_control_send_key_event` / `VirtualKey_Send_KeyCode`. |
| `SendInputString` | `Cmd`: text/base64; `DataOfCmd`: often `base64` | Commits IME text through `remote_control_send_commit_string`. |
| `SendInputEnd` | none required | Ends IME input. |
| `CreateTouchDevice` | touch metadata | Creates virtual touch device. |
| `DestroyTouchDevice` | none seen | Destroys virtual touch device. |
| `ProcessTouchDevice` | touch coordinates/state | Touch input. |
| `ProcessMouseDevice` | `Cmd`: `Move`, `LeftClick`, `LeftPress`, `LeftRelease`, `RightClick`; `Position`: `x`, `y`, `Time` | Virtual mouse move/button/scroll. |
| `SendGamepadKey` | gamepad key fields | Gamepad key event. |
| `SendGamepadMove` | gamepad abs/move fields | Gamepad axis/move event. |

`msf-server` embeds a huge `KEY_*` table, including `KEY_HOME`, `KEY_POWER`, `KEY_HDMI`, `KEY_VOLUP`, `KEY_VOLDOWN`, `KEY_CHUP`, `KEY_CHDOWN`, `KEY_AMBIENT`, `KEY_MULTI_VIEW`, `KEY_ROTATE_PANEL`, and many more.

## Art App Channel

Art app package: `/opt/usr/apps/org.tizen.art-app`, version `3.50.104`.

The Art app registers MSF channel `com.samsung.art-app` from `ArtDataManagement.dll`.

Outer request:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "art_app_request",
    "to": "host",
    "data": "{\"request\":\"api_version\",\"id\":\"...\",\"request_id\":\"...\"}"
  }
}
```

Outer response event:

```text
d2d_service_message
```

The response `data` is a JSON string. Most direct responses contain:

```json
{
  "event": "<request name>",
  "request_id": "<same request_id>"
}
```

If `request_id` is missing, the app sets `request_id` to the entire incoming JSON string. Always send one.

Errors use:

```json
{
  "event": "error",
  "request_id": "...",
  "request_data": "{original request json}",
  "error_code": "-7"
}
```

Error code enum:

| Code | Name |
|---:|---|
| `-14` | `INSUFFICIENT_SYSTEM_SPACE` |
| `-13` | `PREVIEW_NOT_STARTED` |
| `-12` | `CHECKOUT_IN_PROGRESS` |
| `-11` | `INSUFFICIENT_SPACE` |
| `-10` | `TEMPORARILY_UNAVAILABLE` |
| `-9` | `NOT_SUPPORTED_API` |
| `-8` | `SSO_REQUIRED` |
| `-7` | `INVALID_PARAMETER` |
| `-6` | `REQUEST_PARSE_FAIL` |
| `-5` | `DB_ERROR` |
| `-4` | `FILE_NOT_FOUND` |
| `-3` | `NO_MEMORY` |
| `-2` | `NO_PERMISSION` |
| `-1` | `SYSTEM_FAIL` |
| `0` | `NO_ERROR` |

### Art Requests

These request names are in `MobileCommandFactory`.

| Request | Params | Response fields / notes |
|---|---|---|
| `api_version` | none | `version`: `5.0.1.0`. |
| `bl_auto_wall_pattern` | `key` | Ambient/Blueline wallpaper helper. Responds `stat`, `key`, plus ambient info. |
| `bl_image` | `type`, `key`, `fileid`, optional `duration`, `pattern_type`, `install_type`, `wall_color`, `pattern_color` | Downloads/sets Blueline image. Responds `stat`. |
| `bl_marker` | `key` | Ambient/Blueline marker helper. Responds `stat`, `key`, plus ambient info. |
| `buy_content` | `content_id` | Starts purchase checkout. Errors include `SSO_REQUIRED`, `CHECKOUT_IN_PROGRESS`. |
| `change_favorite` | `content_id`, `status`: `on`/`off` | Responds `content_id`, `status`; may broadcast `favorite_changed`. |
| `change_matte` | `content_id`, `matte_id`, optional `portrait_matte_id` | Responds changed matte ids. |
| `current_app` | none | Responds `stat: ok`, plus `current_app_id`, `ambient_mode`. |
| `delete_image_list` | `content_id_list`: array | Responds `content_id_list`; may broadcast `image_deleted`. |
| `enabled_routine` | `routine`: array of objects with `routine_id` | Responds `stat: ok`, plus ambient info. |
| `get_art_picture_mode` | none | Responds `art_picture_mode`. |
| `get_artmode_settings` | none | Responds `data`: JSON string list of setting objects. Includes `brightness`, `color_temperature`, `motion_sensitivity`, `motion_timer`, `brightness_sensor_setting` where supported, each with `value`, `min`, `max` or `valid_values`. |
| `get_artmode_status` | none | Responds `value`: `on`/`off`. |
| `get_content_list` | `category_id` | Responds `content_list`: JSON string list with `content_id`, `category_id`, `slideshow`, and for photos `matte_id`, `portrait_matte_id`, `width`, `height`, `image_date`, `content_type`. |
| `get_content_matte_list` | `category_id`, optional `sub_category_id` | Responds `content_matte_list`: JSON string list of `content_id`, `matte_id`, `portrait_matte_id`. |
| `get_current_artwork` | none | Responds `content_id`, `matte_id`, `portrait_matte_id`, `category_id`, `content_type` (`ambient`, `myphoto`, `artstore`, `na`). |
| `get_current_rotation` | none | Responds `current_rotation_status`: `1` landscape, `2` portrait. |
| `get_device_info` | none | Responds `current_rotation_status`, `support_brightness_sensor`, `support_motion_sensor`, `resolution_type`, `support_color_tone`, `tv_flash_size`, `support_myshelf`, `server_sync_state`, `support_subscription_hub`. |
| `get_matte_list` | none | Responds `matte_type_list` and `matte_color_list` as JSON strings. Color entries contain `color`, `R`, `G`, `B`. |
| `get_photo_filter_list` | none | Responds `filter_list`: JSON string list of objects with `filter_id`. |
| `get_slideshow_status` | none | Responds `value`, `category_id`, `sub_category_id`, `current_content_id`, `type`, `content_list`. `value: off` when disabled; otherwise interval minutes. |
| `get_sso_login_status` | none | Responds `is_logged_in`: `Yes`/`No`. |
| `get_subscription_list` | none | Responds `rsp`; requires SSO. |
| `get_subscription_user_list` | none | Responds `rsp`; requires SSO. |
| `routine_available_app_list` | none | Responds `routine_app`: JSON string/list of routine app ids. |
| `reset_brightness` | none | Responds `brightness_value`. |
| `select_image` | `content_id`, `category_id`, optional `sub_category_id`, `show`: bool | Responds `content_id`, `category_id`, `sub_category_id`, `matte_id`, `portrait_matte_id`, `is_shown`: `Yes`/`No`; broadcasts `image_selected`. |
| `set_art_picture_mode` | `art_picture_mode`: number | Responds `value`. |
| `set_artmode_status` | `value`: `on`/`off` | Responds `status`; may broadcast `art_mode_changed`. |
| `set_bl_adjustment` | `function`: `brightness` or `colortone`; `value`: number | Ambient/Blueline setting. Responds `stat`. |
| `set_brightness` | `value`: number | Responds `value`. |
| `set_brightness_sensor_setting` | `value`: string/number accepted by ScreenManager | Responds `value`. |
| `set_color_temperature` | `value`: number | Responds `value`. |
| `set_motion_sensitivity` | `value`: supported sensitivity string/number | Responds `value`. |
| `set_motion_timer` | `value`: `off`, `always`, `5`, `15`, `30`, `60`, `120`, `180`, `240` depending model mode | Responds `value`. |
| `set_photo_filter` | `content_id`, `filter_id` | Responds `content_id` on success. |
| `set_slideshow_status` | `value`, `category_id`, `sub_category_id`, `type`: `slideshow` or `shuffleslideshow` | Responds same fields; `value: off` disables. |
| `start_preview` | `content_id`, `category_id`, optional `sub_category_id`, `matte_id`, `portrait_matte_id` | Starts preview flow; broadcasts `preview_started`; errors include `INVALID_PARAMETER`, `REQUEST_PARSE_FAIL`, `TEMPORARILY_UNAVAILABLE`. |
| `stop_preview` | none | Stops preview flow; broadcasts `preview_stopped`. |
| `subscribe` | `subscribe_id` | Starts subscription checkout; requires SSO. |
| `tv_information` | none | Responds `stat`, `lang`, `countrycode`, `modelid`, `firmcode`, `resolution`, `smartTVclient`, `DUID`, `color_sensor`, `lifeStyleType`. |
| `unsubscribe` | none seen in parser | Starts unsubscribe/cancel flow; requires SSO. |
| `update_ambient_frame` | `type`, `wallpaperid` | Ambient frame/wallpaper update. Responds `stat`. |
| `update_ambient_setting` | any of `brightness`, `colortone`, `saturation`, `color_r`, `color_g`, `color_b`, `auto_brightness` | Sets ambient picture settings. Responds `stat: ok`. |
| `update_ambient_wallpaper` | `type`, `wallpaperid`, optional Blueline fields `duration`, `pattern_type`, `install_type`, `wall_color`, `pattern_color` | Updates ambient wallpaper. Responds `stat`. |
| `update_routine` | `routine_id` | Updates/launches ambient routine. Responds `stat`. |
| `update_template_config` | `template_app_id`, `template_config_id`, optional `content_info` | Updates ambient template config. Responds `stat`, `previous_app_id`, `current_app_id`. |

### Art Content-Sharing Requests

These are in `MobileDefine.CossList`; they first create a D2D content-sharing channel using `conn_info`.

| Request | Params | Response / behavior |
|---|---|---|
| `get_thumbnail_list` | `content_id_list`, `conn_info`: object/string with `connection_id`, `d2d_mode`, etc. | Responds `content_id`, `file_type`, `content_list`, `conn_info`, then streams/copies thumbnail data over the D2D content-sharing channel. |
| `get_photo_filter_thumbnail_list` | `filter_id_list`, `conn_info` | Responds `conn_info`, then streams/copies filter thumbnails. |
| `send_image` | `file_size`, `file_type`, `matte_id`, `portrait_matte_id`, optional `image_date`, `conn_info` | First responds `ready_to_use` with `conn_info`; after transfer responds `content_id`, matte ids, `width`, `height`; broadcasts `image_added`. |
| `preview_image` | `file_size`, `matte_id`, `portrait_matte_id`, `conn_info` | First responds `ready_to_use`; then previews transferred image. |
| `send_image_list` | `file_size`, `content_list`, `conn_info` | Multi-image upload. Broadcasts `image_of_list_added` per item and `image_list_added` at completion. |
| `send_image_list_with_launch` | same as `send_image_list` | Launches Art app loading screen first if needed, then behaves like multi-image upload. |
| `cancel_image_list` | `request_id` of active COSS request | Cancels active list upload; responds `event: cancel_image_list`. |

### Art Broadcast Events

All are published as `d2d_service_message` on `com.samsung.art-app`.

| Inner `event` | Fields |
|---|---|
| `notify.reset_my_photo` | `stat` |
| `art_mode_changed` | `status` |
| `image_added` | `content_id`, `category_id`, `matte_id`, `portrait_matte_id`, `width`, `height` |
| `image_selected` | `content_id`, `matte_id`, `portrait_matte_id`, `is_shown` |
| `image_deleted` | `content_id` |
| `matte_changed` | `content_id`, `matte_id`, `portrait_matte_id` |
| `buy_checkout_finished` | `content_id`, `status` |
| `preview_started` | none |
| `preview_stopped` | none |
| `subscription_checkout_finished` | `subscription_id`, `status` |
| `subscription_changed` | `is_subscribed` |
| `sso_login_status_changed` | `is_logged_in` |
| `go_to_standby` | none |
| `wakeup` | none |
| `recently_set_updated` | `recently_set_list` |
| `favorite_changed` | `content_id`, `status` |
| `slideshow_image_changed` | `current_content_id`, `type` |
| `slideshow_changed` | `value`, `category_id`, `sub_category_id`, `type` |
| `purchased_information_updated` | none |
| `rotation_changed` | `current_rotation_status` |
| `image_list_added` | `content_list` |
| `image_of_list_added` | `file_name`, `content_id` |
| `notify.sync_server` | `status`: `start`/`finish` |

## Important Absences On This Firmware

These appear in external clients or compatibility code, but are not present in the decompiled `MobileCommandFactory` or `CossList` for this TV firmware:

| Request | Decompile finding |
|---|---|
| `get_api_version` | Not mapped. Use `api_version`. |
| `get_brightness` | Not mapped. Use `get_artmode_settings` and read item `brightness`. |
| `get_color_temperature` | Not mapped. Use `get_artmode_settings` and read item `color_temperature`. |
| `get_thumbnail` | Not mapped. Use `get_thumbnail_list` COSS path. |
| `get_auto_rotation_status` / `set_auto_rotation_status` | Not mapped. Use `get_slideshow_status` / `set_slideshow_status`. |

## Minimal Examples

Art API version:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "art_app_request",
    "to": "host",
    "data": "{\"request\":\"api_version\",\"id\":\"1\",\"request_id\":\"1\"}"
  }
}
```

Get Art Mode settings, including brightness and color temperature:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "art_app_request",
    "to": "host",
    "data": "{\"request\":\"get_artmode_settings\",\"id\":\"2\",\"request_id\":\"2\"}"
  }
}
```

Set Art Mode brightness:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "art_app_request",
    "to": "host",
    "data": "{\"request\":\"set_brightness\",\"value\":5,\"id\":\"3\",\"request_id\":\"3\"}"
  }
}
```

Set slideshow:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "art_app_request",
    "to": "host",
    "data": "{\"request\":\"set_slideshow_status\",\"value\":\"30\",\"category_id\":\"MY-C0002\",\"sub_category_id\":\"\",\"type\":\"slideshow\",\"id\":\"4\",\"request_id\":\"4\"}"
  }
}
```
