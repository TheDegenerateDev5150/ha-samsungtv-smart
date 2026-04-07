Now i saw, you already have an action "select_picture_mode" but this returns the following error:

<details>
<summary>show error message</summary>

Logger: homeassistant.helpers.script.websocket_api_script
Quelle: helpers/script.py:531
Erstmals aufgetreten: 15:19:58 (4 Vorkommnisse)
Zuletzt protokolliert: 15:36:10

websocket_api script: Error executing script. Unexpected error for call_service at pos 1: EnumType.__call__() got an unexpected keyword argument 'component_id'
Traceback (most recent call last):
  File "/usr/src/homeassistant/homeassistant/helpers/script.py", line 531, in _async_step
    await getattr(self, handler)()
  File "/usr/src/homeassistant/homeassistant/helpers/script.py", line 1018, in _async_step_call_service
    response_data = await self._async_run_long_action(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<9 lines>...
    )
    ^
  File "/usr/src/homeassistant/homeassistant/helpers/script.py", line 631, in _async_run_long_action
    return await long_task
           ^^^^^^^^^^^^^^^
  File "/usr/src/homeassistant/homeassistant/core.py", line 2817, in async_call
    response_data = await coro
                    ^^^^^^^^^^
  File "/usr/src/homeassistant/homeassistant/core.py", line 2860, in _execute_service
    return await target(service_call)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/src/homeassistant/homeassistant/helpers/service.py", line 834, in entity_service_call
    single_response = await _handle_entity_call(
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^
        hass, entity, func, data, call.context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/usr/src/homeassistant/homeassistant/helpers/service.py", line 906, in _handle_entity_call
    result = await task
             ^^^^^^^^^^
  File "/config/custom_components/samsungtv_smart/media_player.py", line 2108, in async_select_picture_mode
    await self._st.async_set_picture_mode(picture_mode)
  File "/config/custom_components/samsungtv_smart/api/smartthings.py", line 573, in async_set_picture_mode
    cmd = Command(
        component_id=COMPONENT_MAIN,
    ...<2 lines>...
        arguments=[mode],
    )
TypeError: EnumType.__call__() got an unexpected keyword argument 'component_id'
</details>

Also i do not have a list of supported picture modes in my attributes of the media_player entity, only this:

source_list: TV, HDMI
ip_address: 192.168.1.140
art_mode_status: off
device_class: tv
friendly_name: TV Wohnen
supported_features: 221117
volume_level: 0.12
is_volume_muted: false
media_content_type: video
app_id: TV/HDMI
source: TV/HDMI
frame_art_last_result: 
error: Frame TV not supported
