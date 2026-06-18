# Samsung ExLink / RS-232 Decompile

Device: Samsung QN55LS03FAFXZA
Samsung support: https://www.samsung.com/us/support/downloads/?model=N0003009&modelCode=QN55LS03FAFXZA
Documented: 2026-06-18
Firmware: T-PTMFAKUC-0090-1296.8
Tizen: 9.0.0
Linux: 5.4.261 armv7l

## Sources

Live OS state:

- `/proc/cmdline`
- `/proc/tty/drivers`
- `/proc/consoles`
- `/sys/class/tty/*`
- `/sys/firmware/devicetree/base`
- `systemctl status`
- `gdbus introspect --system`

Pulled from the TV:

- `/usr/bin/TIFADaemon_L`
- `/usr/lib/libIUARTService.so`
- `/usr/bin/TIFSDaemon`
- `/usr/bin/automation-helper`
- `/usr/bin/vddebugmenu`
- `/prd/usr/bin/kfactoryd`
- `/prd/usr/bin/kfactoryd.sh`
- `/usr/lib/modules/5.4.261/kernel/kfactory_drv.ko`
- `/lib/modules/linux/kernel/kfactory_drv.ko`
- `/usr/lib/systemd/system/org.tizen.tv.automation-service.service`
- `/usr/lib/systemd/system/org.tizen.tv.automation-service.path`
- `/usr/lib/systemd/system/org.tizen.tv.factory-service.service`
- `/usr/lib/systemd/system/dlogutil.service`
- `/prd/etc/HyperUART/huart0_ipsetting.sh`
- `/prd/etc/HyperUART/huart_lib.sh`
- `/prd/etc/HyperUART/sdbd_start.sh`
- `/usr/lib/udev/rules.d/60-serial.rules`

## Short Answer

Yes, the operating system has an ExLink / RS-232 handling stack.

The main responder is:

- service: `org.tizen.tv.automation-service`
- process: `/usr/bin/TIFADaemon_L`
- D-Bus object: `/TIFacAutoObj`
- D-Bus interface: `org.tizen.tv.automationservice`
- unit: `/usr/lib/systemd/system/org.tizen.tv.automation-service.service`
- activation path: `/usr/lib/systemd/system/org.tizen.tv.automation-service.path`
- trigger file: `/tmp/AFTER_PRODUCTION`

On this TV, the service was active as root. It exports methods for Ex-UART, RS-232 ACKs, serial source packet length, baud-rate changes, RJP data, and SS/EP/RJP protocol reads.

There does not appear to be a separate `exlinkd` daemon or TCP listener. The OS interface is D-Bus plus native UART devices.

## Runtime Services

| Unit / Process | Runs As | Purpose |
| --- | --- | --- |
| `org.tizen.tv.automation-service.service` -> `/usr/bin/TIFADaemon_L` | root | Main Ex-UART / RS-232 / automation protocol daemon. Owns `org.tizen.tv.automation-service` on the system bus. |
| `org.tizen.tv.factory-service.service` -> `/usr/bin/TIFSDaemon` | root | Factory service. Imports Ex-UART client APIs and factory power/jack controls, but is not the primary byte-stream handler. |
| `/prd/usr/bin/kfactoryd` | root | Bridges factory userspace to `/dev/kfactory`. Not the ExLink byte-stream daemon. |
| `dlogutil.service` -> `/usr/bin/print_dlog.sh` | root | Sends logs to the tty console path. Debug/console plumbing, not ExLink protocol handling. |

## Kernel And Device Clues

`/proc/cmdline` contains:

```text
console=ttyS3,115200N8 rs232=1 model=4kframe
```

`/proc/consoles` reports:

```text
ttyS3 -W- (EC p ) 204:67
```

Serial drivers:

| Driver | Device Prefix | Notes |
| --- | --- | --- |
| `sdp-uart2` | `/dev/ttyS*` | Samsung platform UARTs. |
| `sdp-uart2` | `/dev/ttySD*` | Additional Samsung platform serial device range. |
| `usbserial` / `cp210x` | `/dev/ttyUSB*` | Silicon Labs CP2102N USB-to-UART. |

Observed serial devices:

| Device | Driver / Source | Notes |
| --- | --- | --- |
| `/dev/ttyS0` | `sdp-uart2` | Platform UART. |
| `/dev/ttyS1` | `sdp-uart2` | Platform UART. |
| `/dev/ttyS2` | `sdp-uart2` | Device tree describes `serial@00550F00` as `CEC interface with OCBox using ttyS2`. |
| `/dev/ttyS3` | `sdp-uart2` | Kernel console from `console=ttyS3,115200N8`. |
| `/dev/ttySD0` | `sdp-uart2` | Additional Samsung serial device. |
| `/dev/ttyUSB0` | `cp210x` | Silicon Labs CP2102N USB-to-UART. Symlinked as `/dev/ttyIOT`. |

The pulled automation binary references this device-tree path:

```text
/proc/device-tree/factory/samsung,ex-link_uart
```

That exact node was not present on this live firmware. The binary falls back through platform APIs such as `ppi_link_uart_get_node`, so the ExLink UART path is probably resolved by platform/power-control code rather than by that literal node on this model.

## Automation D-Bus API

Live introspection:

```text
bus:       org.tizen.tv.automation-service
object:    /TIFacAutoObj
interface: org.tizen.tv.automationservice
```

Methods:

| Method | Signature | Notes |
| --- | --- | --- |
| `SendRS232Ack` | `in i pType, in i pLen, in au pData, out (i) ret` | Sends an RS-232 ACK-style response. |
| `SendMessageByExUart` | `in i pLen, in au pData, out (i) ret` | Sends raw bytes through the Ex-UART path. |
| `ExecuteCommand` | `in i data0, in i data1, out (i) ret` | Generic automation command. |
| `ExecuteCommandWithData` | `in i data0, in i data1, in au data, in i len, out (i) ret` | Generic automation command with byte payload. |
| `GetSsProtocolData` | `out au data, out (i) ret` | Reads SS protocol data. |
| `GetEpProtocolData` | `out au data, out (i) ret` | Reads EP protocol data. |
| `CloseExUart` | `out (i) ret` | Closes the Ex-UART path. |
| `ChangeBaudRateExUart` | `in i bdrate, out (i) ret` | Changes Ex-UART baud-rate enum/value. |
| `ChangePacketLengthSerialSource` | `in i len, out (i) ret` | Changes expected packet length for serial-source mode. |
| `SendRjpData` | `in i pLen, in au pData, out (i) ret` | Sends RJP protocol data. |
| `GetRjpProtocolData` | `out au data, out (i) ret` | Reads RJP protocol data. |

Signals:

| Signal | Signature | Notes |
| --- | --- | --- |
| `ep_handler` | `s ep_description` | EP protocol callback. |
| `ss_handler` | `s ss_description` | Serial-source protocol callback. |
| `rjp_handler` | `s rjp_description` | RJP protocol callback. |

## On-Wire FAnet Frames

The UART parser in `FAnetParserBase::IsData` does not parse ASCII Samsung Ex-Link strings. It parses a binary factory automation protocol.

General frame:

```text
1f HH OP DATA... XX
```

Where:

- `1f` is the start byte.
- `HH = ((data_len & 0x1f) << 3) | msg_type`.
- `OP` is the command/opcode byte.
- `DATA` is `data_len` bytes.
- `XX = HH xor OP xor DATA[0] xor ... xor DATA[n-1]`.

Parser constraints recovered from `FAnetParserBase::IsData`:

- Total parsed frame size is `(HH >> 3) + 4`.
- `OP` must be `<= 0xfd`; `0xfe` and `0xff` are rejected.
- `data_len` must be non-zero.
- Inbound frames reject `msg_type` values with bit 2 set. Use `msg_type = 0` for commands.
- Normal one-byte command frames are therefore:

```text
1f 08 OP DATA XX
```

Example frame builder:

```text
frame(op, data) = [1f, 08, op, data, 08 xor op xor data]
```

Examples:

| Operation | Bytes to write |
| --- | --- |
| Set picture mode: Dynamic (`OP=40`, `DATA=03`) | `1f 08 40 03 4b` |
| Set picture mode: Standard (`OP=40`, `DATA=04`) | `1f 08 40 04 4c` |
| Energy saving off (`OP=2e`, `DATA=00`) | `1f 08 2e 00 26` |
| Energy saving high (`OP=2e`, `DATA=03`) | `1f 08 2e 03 25` |
| Read option/version line set (`OP=24`, `DATA=00`) | `1f 08 24 00 2c` |
| Read AVOC backlight through EPA path (`OP=d1`, `DATA=08`) | `1f 08 d1 08 d1` |
| Factory UART mode off-ish (`OP=83`, `DATA=00`) | `1f 08 83 00 8b` |
| Factory UART mode / baud path (`OP=83`, `DATA=01`) | `1f 08 83 01 8a` |
| Factory UART mode / baud path (`OP=83`, `DATA=02`) | `1f 08 83 02 89` |
| Panel factory-in mode (`OP=d3`, `DATA=01`) | `1f 08 d3 01 da` |

The examples above are binary byte sequences, not ASCII hex strings.

## Response Frames

Outbound response frames are built by `FAnetInspectionBase::t_SendMessage`.

| Message Type | Builder | Meaning |
| --- | --- | --- |
| `1` | `t_SendAckMsg` | ACK. Usually sends one data byte, often `02`. |
| `2` | `t_SendData` | Data response. |
| `3` | `t_SendInfoData` | Info response. |
| `4` | `t_SendSkipCode` | Skip-code response. |
| `5` | `t_SendErrorCode` | Error response. |
| `6` | `t_SendReturnMsg` | Result/return response. |

For a one-byte return response, `HH = (1 << 3) | 6 = 0x0e`.

Example success return for opcode `40`:

```text
1f 0e 40 01 4f
```

Example failure/false return for opcode `40`:

```text
1f 0e 40 00 4e
```

## Main Command Opcodes

The primary dispatcher is `FAnetInspection::t_ProcessAutoRemocon`. It logs:

```text
AR Start ClientType[%d] OpCode[0x%02X][0x%02X]
```

The first logged byte is `OP`; the second is the first data byte.

| OP | DATA | Handler | Effect |
| --- | --- | --- | --- |
| `15` | `01` | factory reset path | Calls the same internal helper used by `m_ExecuteFactoryReset`. Destructive. |
| `1e` | `01`, `02` | `m_ExecutePortlandTest` | Portland motor test. `02` displays result. |
| `24` | `00` or line number | `m_ExecuteOptionReading` | Reads `factory_get_version_info`. `00` sends all parsed lines; non-zero sends one line. |
| `2e` | `00`-`04` | `m_ExecuteEnergySaving` | Calls `avoc_set_energy_saving`. `00/04` off, `01` low, `02` medium, `03` high. |
| `2f` | any | `t_SendTvViewerKey` | Sends TV viewer key `discrete=disc_hdmi1`. |
| `35` | `01` | `m_ExecuteTConDownload` | Sets factory parameter `0x86b`, checks it, displays OK/NG. |
| `40` | `00`, `01`, `03`, `04`, `05`, `08`, `09`, `0a`, `0b` | `t_ExecuteMovieMode` | Picture-mode/factory-WB path. Calls `avoc_set_picture_mode`, `avoc_reset_picture`, and sometimes `ppi_ve_set_condition`. |
| `61` | `00`-`06` | `t_ExecuteFactory` | Factory serial/projector control. Sets factory params `0x212`, `0x311`, `0x16`; data `06` displays `USB Serial : Projector` if supported. |
| `72` | `01`-`06`, `10`, `11`, `a0`-`aa` | `m_ExecuteLocalDimming` | Local dimming tests and factory-item writes. |
| `76` | `05`, `06` | `m_ExecuteCheckTconStatus` | `05` OLED off-sensing, `06` fast off-sensing. |
| `7a` | byte | `t_ExecuteWIFIStaticConnecting` | Stores Wi-Fi/static byte 0. |
| `7c` | byte | `t_ExecuteWIFIStaticConnecting` | Stores Wi-Fi/static byte 1. |
| `7d` | byte | `t_ExecuteWIFIStaticConnecting` | Stores Wi-Fi/static byte 2. |
| `7e` | byte | `t_ExecuteWIFIStaticConnecting` | Stores Wi-Fi/static byte 3. |
| `7f` | byte | `t_ExecuteWIFIStaticConnecting` | Stores Wi-Fi/static byte 4, then may enter production mode when all bytes are present. |
| `82` | `00`, `01`, `02`, `03`, `12`, `f0` | `m_ExecuteFastBootInProduction` | Fast-boot production flag, query, reboot, production-mode transition, or poweroff. Destructive for `03`, `12`, `f0`. |
| `83` | `00`-`03` | `t_ExecuteFactory` | Factory UART/RS-232 mode. Sets factory param `0x16`; `01` changes baud enum `0`, `02` changes baud enum `1` after recreating/closing path. |
| `88` | `00`-`04` | `t_ExecuteVFProcessLine` | VF/PBA process-line modes. Data `01` sets PBA-test condition; `04` disables OSD and sends an internal message. |
| `d1` | `01`-`0d` | `m_ExecuteEPATest` | EPA/factory/AVOC read path. See EPA table below. |
| `d3` | `00`, `01`, `02` | `m_ExecutePanelFactoryMode` | Factory-in/out mode. Calls `ppi_ve_set_condition`, `avoc_reset_picture`, or `avoc_set_factory_out`. |
| `e3` | byte | `t_ExecuteBTPairing` | Bluetooth pairing/MAC-byte staging if BT is supported. |
| `e4` | byte | Wi-Fi byte staging | Stores `t_WiFiInfo[4]`, marks byte present. |
| `e5` | any | `m_ExecuteMediaBoxFuncTest` | Explicitly returns Not Support. |
| `ed` | `02`, `04`, `09`, `0b` | `m_ExecuteSwAutoUpdate` | MICOM firmware upgrade, SWU flag, sub-OTP update/reboot, or LD firmware update. Destructive. |
| `f0`-`f8` | byte | `t_ExecuteBTPairing` | Bluetooth pairing/MAC-byte staging. |
| `f9` | byte | `t_ExecuteWIFIConnecting` | Stores Wi-Fi byte 0. |
| `fa` | byte | `t_ExecuteWIFIConnecting` | Stores Wi-Fi byte 1. |
| `fb` | byte | `t_ExecuteWIFIConnecting` | Stores Wi-Fi byte 2, then may enter production mode when all bytes are present. |
| `fc` | byte | `t_ExecuteWIFIConnecting` | Routed to Wi-Fi handler; decompiled handler does not store a new byte for this opcode. |
| `fd` | any | success-only branch | Disables OSD path and returns success. Exact external purpose unclear. |

## EPA Read Subcommands

`OP=d1` is the clearest useful read path.

| DATA | Function |
| --- | --- |
| `01` | `factory_get_eerc_version` |
| `02` | `factory_get_data(0x6f)` |
| `03` | `factory_get_data(0x515)` |
| `04`, `0c` | `factory_get_data(0x516)` |
| `05`, `0d` | `factory_get_data(0x6a7)` |
| `06` | `factory_get_str_data(0x2390)` |
| `07` | `avoc_get_contrast(0, ..., AVOC_SAVE)` |
| `08` | `avoc_get_backlight(0, ..., AVOC_SAVE)` |
| `09` | `avoc_get_brightness(0, ..., AVOC_SAVE)` |
| `0a` | `avoc_get_motion_lighting(0, ...)` |
| `0b` | `avoc_get_eco_sensor(0, AVOC_SAVE, ...)` |

So the binary ExLink/FAnet way to read backlight is:

```text
1f 08 d1 08 d1
```

No direct `avoc_set_backlight` command was found in this UART parser. `avoc_set_backlight` is imported by the daemon, but the recovered ExLink/FAnet auto-remocon dispatch exposes `avoc_get_backlight` through `OP=d1, DATA=08`, not a matching setter.

## Other Subprotocols

`CAutoAVControlBase::IsData` accepts a separate 7-byte inner AV-control packet:

```text
08 22 B2 B3 B4 B5 CC
```

Where:

```text
CC = -(08 + 22 + B2 + B3 + B4 + B5) & ff
```

When valid, the daemon:

- forwards `B2 B3 B4 B5` to the registered AV-control callback;
- sends ACK bytes `03 0c f1` through `FAnetClient::SendMessage`.

`RJPProtocolControl::IsData` accepts RJP data only when hotel mode is enabled. The first packet must start:

```text
02 00 cb ...
```

The buffered RJP size is calculated as:

```text
size = buffer[3] + 6
```

It also has a loopback-test check for an RJP packet with byte `3 == 04` and the following little-endian word `a5 a6 a7 a8`.

## Native Symbols

`/usr/bin/TIFADaemon_L` contains the actual ExLink/RS-232 implementation. Important symbols and strings include:

| Symbol / String | Meaning |
| --- | --- |
| `IFAnetUtil::GetUartPath(char*)` | Resolves the UART device used by the automation stack. |
| `FAnetUartClientBase::m_OpenUart(char const*, FAnetBaudRate_e)` | Opens the UART. |
| `FAnetUartClientBase::m_CloseUart()` | Closes the UART. |
| `FAnetUartClientBase::ChangeBaudrate(FAnetBaudRate_e)` | Changes UART baud rate. |
| `FAnetUartClientBase::m_ReceiveData(unsigned char*, int*)` | Receives UART data. |
| `FAnetUartClientBase::t_SendMessage(unsigned char*, int, FAnetMessageArgs_s)` | Sends UART data. |
| `FAnetUartClientBase::t_check_micom_serial_mode()` | Checks MICOM serial mode. |
| `FAnetParser`, `FAnetParserBase` | Parses FAnet / automation serial packets. |
| `FAnetInspection`, `FAnetInspectionBase` | Factory inspection command handling. |
| `RJPProtocolControl` | RJP protocol handling. |
| `CAutoAVControlBase` | Automation AV control path. |
| `IRInput`, `IRInputBase` | Auto remote / IR input path. |
| `factory_set_rs232jack` | Factory API for RS-232 jack selection/config. |
| `ppi_powercontrol_diag_set_uart_port_type` | Platform power-control UART mode selection. |
| `ppi_link_uart_get_node` | Platform API to resolve the link UART node. |
| `ppi_link_uart_select_mb_uart` | Platform API to select main-board UART routing. |
| `avoc_set_backlight`, `avoc_get_backlight` | Automation stack can reach AVOC backlight functions. |

Useful log strings from `TIFADaemon_L`:

```text
GetUartPath
failed to get uart node [%d]
GetUartPath success %s
*** GetUartPath FAILURE ***
Uart: siRs232Jack[%d]
rs232
rs232=%d
micom_serial_mode = %d
Dev[%s] BaudRate[%s]
ChangeBaudrate Done m_DevicePath[%s] mUartHandle[%d]
RS232:%d, USB Serial:%d
RS232 change from FANET to UART[%d], ret = %d
```

## Client Library

`/usr/lib/libIUARTService.so` is a client/wrapper library for the automation-service D-Bus API.

Important strings:

```text
org.tizen.tv.automation-service
org.tizen.tv.automationservice
SendMessageByExUart
SendRS232Ack
CloseExUart
ChangeBaudRateExUart
ChangePacketLengthSerialSource
automation_register_callback_serial_source
automation_unregister_callback_serial_source
automation_register_callback_rjp_protocol
automation_register_callback_ep_protocol
```

This means native code can talk to the ExLink stack through the library instead of constructing D-Bus messages manually.

## Factory Service Relationship

`/usr/bin/TIFSDaemon` owns:

```text
org.tizen.tv.factory-service
/TIFacSerObj
org.tizen.tv.factoryservice
```

It exposes many generic factory methods such as `GetItem`, `SetParameter`, `Executes`, and `GetSerialNo`.

Relevant ExLink/serial imports in `TIFSDaemon`:

```text
automation_send_message_by_ex_uart
automation_close_ex_uart
ppi_powercontrol_set_exlink_onoff
ppi_powercontrol_diag_set_uart_port_type
ppi_link_uart_get_node
ppi_link_uart_select_mb_uart
ppi_link_ops_test_uart_loopback
```

Interpretation: factory-service can configure or call into the Ex-UART path, but the primary responder/parser is automation-service.

## HyperUART

The TV also has HyperUART scripts under `/prd/etc/HyperUART`.

They configure a `huart0` network interface in the `192.168.250.x` range and can start `sdbd` for Samsung debug-over-UART workflows.

This appears to be a Samsung engineering/debug transport. It is adjacent UART infrastructure, but not the ExLink / RS-232 application protocol handler described above.

## Likely Stack

```text
ExLink / RS-232 connector
  -> One Connect / MICOM / link UART routing
  -> Samsung sdp-uart2 tty device
  -> /usr/bin/TIFADaemon_L
  -> FAnetUartClientBase
  -> FAnetParser / RJPProtocolControl / CAutoAVControlBase
  -> org.tizen.tv.automation-service D-Bus API
  -> native clients through libIUARTService.so
```

## What Is Still Unknown

- The exact physical tty node used for the ExLink connector was not proven from open file descriptors, because root-owned daemon file descriptors were not readable from the available shell.
- The binary references `/proc/device-tree/factory/samsung,ex-link_uart`, but that node is absent on this firmware.
- The strongest live clues are `rs232=1`, the automation-service D-Bus API, `FAnetUartClientBase`, `factory_set_rs232jack`, `ppi_link_uart_get_node`, and the One Connect `ttyS2` device-tree description.
- The exact FAnet/ExLink packet grammar and command IDs require deeper decompilation of `FAnetParserBase`, `FAnetInspectionBase`, and the `ExecuteCommand*` handlers.

## Bottom Line

The ExLink / RS-232 feature is real on this TV and is handled by root userspace code.

The main component is `/usr/bin/TIFADaemon_L`, reachable over system D-Bus as `org.tizen.tv.automation-service` at `/TIFacAutoObj`. It exposes raw Ex-UART send/close/baud methods and protocol-specific SS/EP/RJP methods. Factory-service and kfactory are supporting/control paths, not the main serial protocol endpoint.
