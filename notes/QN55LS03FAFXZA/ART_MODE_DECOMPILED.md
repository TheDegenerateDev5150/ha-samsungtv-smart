# Samsung Art Mode App Decompile

- Device: `QN55LS03FAFXZA`
- Samsung support: https://www.samsung.com/us/support/downloads/?model=N0003009&modelCode=QN55LS03FAFXZA
- Documented: `2026-06-18`
- Firmware: `T-PTMFAKUC-0090-1296.8`
- Tizen: `9.0.0`
- Linux: `5.4.261 armv7l`

## Sources

- Full TV package: `/opt/usr/apps/org.tizen.art-app`
- Manifest: `/opt/usr/apps/org.tizen.art-app/tizen-manifest.xml`
- App/UI assembly: `/opt/usr/apps/org.tizen.art-app/bin/ArtApp.dll`
- Data/protocol assembly: `/opt/usr/apps/org.tizen.art-app/bin/ArtDataManagement.dll`
- Text/resources assembly: `/opt/usr/apps/org.tizen.art-app/bin/ArtAppTextResources.dll`
- Embedded Samsung build root visible in decompiled symbols/log strings: `/home/abuild/rpmbuild/BUILD/org.tizen.art-app-3.50.104/`

Related app packages seen on the TV:

- `/opt/usr/apps/com.samsung.tv.coba.art`
- `/opt/usr/apps/com.samsung.tv.home.art`
- `/usr/apps/com.samsung.tv.wizard.art`
- `/opt/usr/apps/com.samsung.tv.ambientbg-tranquilnature`
- `/opt/usr/apps/com.samsung.tv.ambientfte`
- `/opt/usr/apps/com.samsung.tv.ambientinfo-resources`
- `/opt/usr/apps/com.samsung.tv.ambient-sound`

## Short Answer

Yes. Art Mode is a built-in Tizen .NET app: `org.tizen.art-app`.

The app does not directly own public ports `8001` or `8002`. Those are owned by `msf-server`. Art Mode registers an MSF channel through the TV's SmartView/MSF service and receives websocket messages from `msf-server`.

The important channel is:

- MSF channel: `com.samsung.art-app`
- Incoming event: `art_app_request`
- Outgoing event: `d2d_service_message`

It also opens an IoT/OCF channel named `ambientapp`. Both paths feed the same `MobileProtocolManager`.

## Package Identity

Manifest facts:

- Package: `org.tizen.art-app`
- Version: `3.50.104`
- App id: `org.tizen.art-app`
- Exec: `ArtApp.dll`
- Type: `dotnet-inhouse`
- Launch mode: `single`
- Built-in app: `true`
- Category: `lifestyle`
- API version: `9.0`
- TV info API version: `6.6.0`
- Infolink: `T-INFOLINK2025-1008`

Required packages:

- `csapi-tv-service-ambient`
- `com.samsung.tv.contentimageapp`

Interesting privileges:

- app launch/kill
- network get/set/profile
- Samsung SSO and billing
- product info
- keygrab
- external/mediastorage and content write
- datasharing
- notification
- recorder
- Bluetooth
- Samsung WAS/platform privileges
- package manager info

The manifest also binds a long press of `XF86PowerOff` for 2000 ms to force-launch `org.tizen.art-app` with:

```text
mode:process_long_press
```

## App Layout

Important package files:

| File | Purpose |
|---|---|
| `tizen-manifest.xml` | Package identity, privileges, app-control rules. |
| `ArtApp.deps.json` | .NET dependency manifest. |
| `bin/ArtApp.dll` | App lifecycle, UI, window/state controls. |
| `bin/ArtDataManagement.dll` | Data model, DB/storage, websocket/mobile protocol, Art/Ambient command handlers. |
| `bin/ArtAppTextResources.dll` | Text resource assembly. |
| `bin/ArtDataManagement.xml` | XML docs shipped with the app. |
| `bin/ArtDataManagement.pdb` | Debug symbols present in package. |
| `res/art/*` | Default fullscreen art and thumbnail assets. |
| `res/ambient/*` | Ambient wallpaper/resources. |
| `res/howto/*`, `res/membership/*` | UI resource images. |

## Startup

`ArtApp.Main()` first checks TV feature flags:

- `com.samsung/featureconf/frame_tv`
- `com.samsung/featureconf/ambient_screen_support`
- `com.samsung/featureconf/ambient.tlog_support`

If none are true, the app returns without starting.

When allowed to start, it:

- initializes event/log managers
- writes app logs under `/run/user/5001/artapplog.txt`
- waits for `/run/.wm_ready`
- CPU-boosts the current process for 4000 ms
- starts `FluxApplication`

`OnCreate()` initializes the big app subsystems:

- `DataManager`
- `PerfManager`
- `WindowControl`
- `BGControl`
- `ContentControl`
- `ViewControl`
- `BurnInPreventionControl`
- `AccessibilityControl`
- `BoostControl`
- `SlideShowControl`
- `AmbientContentBGMusicControl`
- `MainControl`
- `DataEventControl`
- `StateControl`

Language is read from:

```text
db/menu_widget/language
```

## App-Control Modes

The app receives launch modes through Tizen `AppControl` extras, especially `mode`.

Important modes seen in the decompile:

| Mode | Meaning |
|---|---|
| `init` | Initial/data startup path. |
| `artboot` | Boot/full-power Art startup path. |
| `process_long_press` | Power-key long press handler. |
| `fullscreen` | Enter Art Mode fullscreen from mobile/API. |
| `fullscreen-forced` | Force fullscreen from navigation state. |
| `exit` | Exit Art Mode. |

`set_artmode_status` uses this same app-control path. It launches `org.tizen.art-app` with `mode=fullscreen`, `mode=fullscreen-forced`, or `mode=exit` and includes `requester=mobile`.

## Data Initialization

Data initialization does the heavy setup:

- reset processing
- `ArtScreenAPI.Initialize()`
- hotel clone DB backup/restore handling
- local DB init
- service support loading
- storage init
- server summary/cache init
- Samsung server manager init
- server-post manager init
- Art Sherpa init
- vconf callbacks
- COSS temp image cleanup
- mobile protocol startup
- SSO control init
- Ambient reset checks
- ambient setting post/sync

This is why Art websocket behavior is app-owned. The websocket request arrives over `msf-server`, but command execution lives inside `ArtDataManagement.dll`.

## Public WebSocket Shape

Outer MSF websocket request:

```json
{
  "method": "ms.channel.emit",
  "params": {
    "event": "art_app_request",
    "to": "host",
    "data": "{\"request\":\"get_artmode_settings\",\"id\":\"1\",\"request_id\":\"1\"}"
  }
}
```

The `data` field is a JSON string. Art Mode parses it and expects at least:

```json
{
  "request": "get_artmode_settings",
  "id": "1",
  "request_id": "1"
}
```

If `request_id` is absent, the app synthesizes one from current ticks.

Responses are sent back over:

```text
d2d_service_message
```

Error responses use:

```json
{
  "event": "error",
  "error_code": -7,
  "request_data": "...",
  "request_id": "..."
}
```

Error enum:

| Code name | Value |
|---|---:|
| `INSUFFICIENT_SYSTEM_SPACE` | `-14` |
| `PREVIEW_NOT_STARTED` | `-13` |
| `CHECKOUT_IN_PROGRESS` | `-12` |
| `INSUFFICIENT_SPACE` | `-11` |
| `TEMPORARILY_UNAVAILABLE` | `-10` |
| `NOT_SUPPORTED_API` | `-9` |
| `SSO_REQUIRED` | `-8` |
| `INVALID_PARAMETER` | `-7` |
| `REQUEST_PARSE_FAIL` | `-6` |
| `DB_ERROR` | `-5` |
| `FILE_NOT_FOUND` | `-4` |
| `NO_MEMORY` | `-3` |
| `NO_PERMISSION` | `-2` |
| `SYSTEM_FAIL` | `-1` |
| `NO_ERROR` | `0` |

## MSF Server Bridge

`MSFServerControl` does this:

- `SmartView.Service.GetLocal(...)`
- `service.CreateChannel("com.samsung.art-app")`
- add listener for `art_app_request`
- pass payload into `MobileProtocolManager.OnReceivedHandler(data, ProtocolType.MSF, client.Id)`
- reply with `channel.Publish("d2d_service_message", data, client)`

So:

- `msf-server` is the public socket owner
- `org.tizen.art-app` is the Art protocol host
- `ArtDataManagement.dll` is where request names and params are implemented

## IoT Server Bridge

`IoTServerControl` checks:

```text
memory/iot/thing/thing_status == 1
```

Then it:

- creates an IoT server through `ServerFactory.Create()`
- opens channel `ambientapp`
- passes received data to `MobileProtocolManager.OnReceivedHandler(data, ProtocolType.IoT)`

This path shares the same command parser as the websocket path.

## Request Dispatch

`MobileProtocolManager` parses incoming JSON and dispatches `request` through `MobileCommandFactory`.

Special handling:

- COSS/image-transfer requests create or use `ContentSharingControl`.
- Some mutating requests require Art disclaimer agreement first.
- Unknown requests return `NOT_SUPPORTED_API`.

COSS/image-transfer request list:

- `get_thumbnail_list`
- `send_image`
- `preview_image`
- `get_photo_filter_thumbnail_list`
- `send_image_list`
- `send_image_list_with_launch`
- `cancel_image_list`

Disclaimer-gated request list:

- `send_image`
- `preview_image`
- `send_image_list`
- `send_image_list_with_launch`
- `select_image`
- `start_preview`
- `set_artmode_status`
- `set_slideshow_status`
- `update_template_config`
- `update_ambient_wallpaper`
- `change_favorite`

## Art Mode Settings Commands

| Request | Params | What it does |
|---|---|---|
| `get_artmode_status` | none | Returns `value`: `off`, `nav`, or `on` from `ArtScreenAPI.GetUIStatus()`. |
| `set_artmode_status` | `{"value":"on"}` or `{"value":"off"}` | Launches `org.tizen.art-app` with `fullscreen`/`fullscreen-forced` or `exit`. |
| `get_artmode_settings` | none | Returns a `data` string containing setting objects for brightness, color temperature, motion sensitivity, motion timer, and brightness sensor. |
| `set_brightness` | `{"value": 25}` | Calls `ArtScreenAPI.SetPictureSetting(ScreenManagerAmbientPictureSetting 0, value)`. |
| `set_color_temperature` | `{"value": 2}` | Calls `ArtScreenAPI.SetPictureSetting(ScreenManagerAmbientPictureSetting 1, value)`. |
| `set_motion_sensitivity` | `{"value": "1"}` through `{"value": "3"}` | Calls `SensorUtil.SetMotionSensitivityValue(value)`. |
| `set_motion_timer` | `{"value":"off"}`, `{"value":"always"}`, `{"value":"5"}`, `{"value":"15"}`, `{"value":"30"}`, `{"value":"60"}`, `{"value":"120"}`, `{"value":"180"}`, `{"value":"240"}` | Uses motion-sensor sleep-after when supported, otherwise `db/art-app/settings/offtimer`. |
| `set_brightness_sensor_setting` | `{"value":"on"}` or `{"value":"off"}` | Calls `ScreenManagerSetBrightnessSensorEnableValue(value == "on")`. |
| `reset_brightness` | none | Calls `DataAPI.ResetBrightness()`, then returns `brightness_value`. |
| `get_current_rotation` | none | Returns `current_rotation_status`: `1` landscape, `2` portrait. |
| `get_art_picture_mode` | none | Calls `ScreenManagerGetAmbientScreenPictureType()` and returns `art_picture_mode`. |
| `set_art_picture_mode` | `{"art_picture_mode": 0}` | Calls `ScreenManagerSetAmbientScreenPictureType()` immediately, or defers via `ArtScreenAPI.LastSavedPictureType` when picture setting mode is active. |

`get_artmode_settings` is the value discovery API. It returns min/max for numeric settings where the platform exposes ranges:

```json
[
  {"item":"brightness","value":"25","min":"0","max":"50"},
  {"item":"color_temperature","value":"2","min":"0","max":"4"},
  {"item":"motion_sensitivity","value":"2","min":"1","max":"3"},
  {"item":"motion_timer","value":"60","valid_values":"[\"off\",\"60\",\"120\",\"180\",\"240\"]"},
  {"item":"brightness_sensor_setting","value":"off"}
]
```

The numbers above are example shape only. The real min/max are returned by:

```text
ScreenManagerGetAmbientPictureSettingRange(...)
```

## Internal Picture Settings

The Art/Ambient picture-setting enum mapping is:

| Internal setting | `ScreenManagerAmbientPictureSetting` |
|---|---:|
| Brightness | `0` |
| Color tone / color temperature | `1` |
| Saturation | `2` |
| Red channel | `3` |
| Green channel | `4` |
| Blue channel | `5` |

The public Art websocket settings expose brightness and color temperature directly. Ambient update paths can also set saturation and RGB channels.

This is separate from the normal TV menu/IP-control backlight path. Art Mode settings use `Tizen.TV.System.Screen` APIs, not `avoc_get_backlight` / `avoc_set_backlight`.

Important platform calls:

- `ScreenManagerSetAmbientScreenPictureModeSync(...)`
- `ScreenManagerSetAmbientScreenPictureMode(...)`
- `ScreenManagerGetAmbientScreenPictureSettingMode(...)`
- `ScreenManagerGetAmbientScreenPictureType(...)`
- `ScreenManagerSetAmbientScreenPictureType(...)`
- `ScreenManagerSetAmbientPictureSettingValue(...)`
- `ScreenManagerGetAmbientPictureSettingValue(...)`
- `ScreenManagerGetAmbientPictureSettingRange(...)`
- `ScreenManagerResetAmbientPictureSettingValue(...)`
- `ScreenManagerSetBrightnessSensorEnableValue(...)`
- `ScreenManagerGetBrightnessSensorEnableValue(...)`
- `ScreenManagerSetMotionSensorSettingValue(...)`
- `ScreenManagerGetMotionSensorSettingValue(...)`

`ArtScreenAPI` chooses `ScreenManagerLifestyleAppType` based on whether the current service is Art vs Ambient. Decompilation shows it passes app type `2` when `IsArtPictureFlag` is true, otherwise app type `1`.

## Content / Artwork Commands

| Request | Params | What it does |
|---|---|---|
| `get_content_list` | `{"category_id":"MY-C0008"}` | Reads content list from local DB/cache for the requested category. |
| `select_image` | `{"content_id":"...","category_id":"...","sub_category_id":"...","show":true}` | Selects current artwork and returns matte IDs. |
| `delete_image_list` | `{"content_id_list":["..."]}` | Deletes selected user images/content records. |
| `change_matte` | `{"content_id":"...","matte_id":"...","portrait_matte_id":"..."}` | Changes matte for existing content. |
| `start_preview` | `{"content_id":"...","category_id":"...","sub_category_id":"...","matte_id":"...","portrait_matte_id":"..."}` | Starts preview for a content item. |
| `stop_preview` | none | Stops preview. |
| `get_matte_list` | none | Returns known matte types/colors. |
| `get_content_matte_list` | `{"category_id":"...","sub_category_id":"..."}` | Returns matte IDs per content item. |
| `get_current_artwork` | none | Returns current content, category, and matte IDs. |
| `get_photo_filter_list` | none | Returns supported photo filters. |
| `set_photo_filter` | `{"content_id":"...","filter_id":"..."}` | Applies a photo filter to a content item. |
| `get_current_rotation` | none | Returns landscape/portrait status. |

## Image Transfer / COSS Commands

These use `ContentSharingControl` and D2D/COSS transfer plumbing.

| Request | Params | What it does |
|---|---|---|
| `get_thumbnail_list` | `{"content_id_list":["..."]}` | Prepares thumbnail transfer and returns `conn_info`. |
| `send_image` | `{"matte_id":"...","portrait_matte_id":"...","file_type":"jpg","image_date":"..."}` | Starts single image upload. |
| `preview_image` | `{"matte_id":"...","portrait_matte_id":"..."}` | Starts preview of uploaded image. |
| `get_photo_filter_thumbnail_list` | `{"filter_id_list":["..."]}` | Prepares filter thumbnail transfer and returns `conn_info`. |
| `send_image_list` | `{"content_list":[...]}` | Starts multi-image upload. |
| `send_image_list_with_launch` | `{"content_list":[...]}` | Starts multi-image upload and launch/show flow. |
| `cancel_image_list` | none | Cancels active multi-image upload. |

## Slideshow Commands

| Request | Params | What it does |
|---|---|---|
| `get_slideshow_status` | none | Returns `value`, category IDs, slideshow type, and serialized content list. |
| `set_slideshow_status` | `{"value":"off"}` or `{"value":"60","category_id":"...","sub_category_id":"...","type":"slideshow"}` | Updates slideshow interval/source/type. |

Known slideshow `type` strings:

- `slideshow`
- `shuffleslideshow`

## Store / Subscription Commands

| Request | Params | What it does |
|---|---|---|
| `buy_content` | `{"content_id":"..."}` | Starts billing checkout for a content item. |
| `get_subscription_user_list` | none | Gets subscription user info. |
| `get_subscription_list` | none | Gets available subscription products. |
| `change_favorite` | `{"content_id":"...","status":"on"}` or `{"status":"off"}` | Sets favorite state in local data. |
| `subscribe` | `{"subscribe_id":"..."}` | Requires SSO, starts subscription checkout. |
| `unsubscribe` | none | Requires SSO, starts unsubscribe flow. |
| `get_sso_login_status` | none | Returns SSO login state. |

## Ambient Commands

These are handled by the same app/package, but are Ambient/lifestyle features rather than narrow Art Mode controls.

| Request | Params seen | What it does |
|---|---|---|
| `api_version` | none | Returns Ambient API version. |
| `bl_auto_wall_pattern` | `{"key":"..."}` | BL/lifestyle auto-wall-pattern path. |
| `bl_image` | `{"type":"...","key":"..."}` | BL/lifestyle image path. |
| `bl_marker` | `{"key":"..."}` | BL/lifestyle marker path. |
| `current_app` | none | Returns current app id/state. |
| `enabled_routine` | routine payload | Routine enable/update path. |
| `set_bl_adjustment` | `{"value":1}` plus command context | Updates BL/lifestyle adjustment. |
| `tv_information` | none | Returns TV/device information. |
| `update_ambient_frame` | `{"type":"..."}` | Updates Ambient frame/style. |
| `update_ambient_setting` | `{"brightness":...}`, `{"colortone":...}`, `{"saturation":...}`, `{"color_r":...}`, `{"color_g":...}`, `{"color_b":...}` | Updates Ambient picture settings through `SettingControl`. |
| `update_ambient_wallpaper` | `{"type":"..."}` | Updates Ambient wallpaper. |
| `update_routine` | routine payload | Updates routine data. |
| `update_template_config` | template/config payload | Updates Ambient template config. |
| `routine_available_app_list` | none | Returns app list for routines. |
| `get_device_info` | none | Returns support flags such as brightness sensor, motion sensor, color tone, resolution type, flash size, My Shelf, sync state, subscription hub. |

## Broadcast / Response Events

Known response/event names embedded in `MobileDefine`:

- `api_version`
- `ready_to_use`
- `notify.reset_my_photo`
- `bl_marker`
- `art_mode_changed`
- `image_added`
- `image_selected`
- `image_deleted`
- `matte_changed`
- `buy_checkout_finished`
- `preview_started`
- `preview_stopped`
- `subscription_checkout_finished`
- `subscription_changed`
- `sso_login_status_changed`
- `go_to_standby`
- `wakeup`
- `recently_set_updated`
- `favorite_changed`
- `slideshow_image_changed`
- `slideshow_changed`
- `purchased_information_updated`
- `rotation_changed`
- `image_list_added`
- `image_of_list_added`
- `cancel_image_list`
- `notify.sync_server`
- `ok`
- `fail`
- `on`
- `off`
- `yes`
- `no`
- `stat`
- `start`
- `finish`

## Storage

Important paths are constructed from Tizen app directories and platform env vars:

| Purpose | Path expression |
|---|---|
| Preinstalled content root | `$TZ_SYS_DATA/org.tizen.art-app/` |
| Preinstalled content | `$TZ_SYS_DATA/org.tizen.art-app/preinstalled_contents/` or `preinstalled_contents_DISNEY/` |
| Download/user data root | app `SharedTrusted` + `data/` |
| Downloaded originals | app `SharedTrusted` + `data/download_contents/` |
| Downloaded thumbnails | app `SharedTrusted` + `data/download_thumbnail_contents/` |
| My Photo root | app `SharedTrusted` + `data/my_photo/` |
| COSS temp image root | app `SharedTrusted` + `data/my_photo/coss/d2d-provider/d2d/` |
| Fullscreen rendered image | app `SharedTrusted` + `data/fullscreen.jpg` |
| Fullscreen preview | app `SharedTrusted` + `data/fullscreen_pre.jpg` |
| Fullscreen metadata | app `SharedTrusted` + `data/FullscreenInfo` |
| Art boot marker | app `SharedTrusted` + `art_boot` |
| Lifestyle home reset flag | app `SharedTrusted` + `lifestyle_home_reset_flag` |
| Power-off guide flag | app `SharedTrusted` + `lifestyle_poweroff_guide_flag` |
| Flash reset flag | `$TZ_SYS_HOME/owner/share/artapp_flashreset_flag` |

## Practical Takeaways

Art Mode is not a simple remote-server feature. It is a full built-in app with its own data manager, UI lifecycle, content DB, Samsung server sync, billing/SSO flows, image transfer service, and mobile/websocket command parser.

For remote control:

- use the generic MSF websocket transport on `8001`/`8002`
- send `ms.channel.emit`
- target event `art_app_request`
- send an inner JSON string with `request`
- read `d2d_service_message` responses

For value discovery:

- call `get_artmode_settings` for brightness/color-temperature ranges and timer values
- call `get_device_info` for sensor/support capability flags
- call `get_art_picture_mode` for the current ambient/art picture type

For setting Art Mode display values:

- `set_brightness` and `set_color_temperature` call `ScreenManagerAmbientPictureSetting`
- `set_brightness_sensor_setting` calls brightness sensor enable APIs
- `set_motion_timer` and `set_motion_sensitivity` call motion/offtimer APIs
- `set_artmode_status` launches/exits the app through Tizen app-control modes
