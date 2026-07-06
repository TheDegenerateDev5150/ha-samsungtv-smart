# SmartThings API usage & polling

Samsung has announced that the SmartThings API is moving to paid tiers, with
free access phasing out around **October 2026** (a **$4.99/month "Personal"
plan** with a monthly call quota, plus separate commercial tiers). Because this
integration's SmartThings calls run **under each user's own Samsung account**,
the cumulative call volume matters. This document explains where the integration
talks to the SmartThings (ST) cloud, and how the polling was reworked in
**8.3.0** to make the **local WebSocket the primary source** and the ST cloud a
throttled fallback.

## What comes from where

| Data | Source |
|---|---|
| Power on/off | **Local** WebSocket (`is_connected`) / IP Control / device-info REST — ST only as a cached refinement |
| Running app, media title | **Local** WebSocket |
| Volume, mute | **Local** UPnP (with ST as backup) |
| Channel number/name | ST cloud only |
| Source / HDMI input labels | ST cloud only |
| Picture mode, sound mode | ST cloud only |
| Power/energy metering, light-sensor lux | ST cloud only |

Only the cloud-only rows require SmartThings; everything else is already local.

## The problem (before 8.3.0)

A fully-equipped Frame TV issued roughly **37 ST HTTP calls/minute** — and it
barely dropped when the TV was off (~36/min), because almost nothing that polled
ST was gated on power. The dominant cost was **`sensor.py`**, not the media
player:

- the **power-consumption sensor ran as 5 separate entities**, each calling
  `get_device_status` on the *same* device every 15 s (**20 calls/min**);
- the illuminance and brightness child sensors added **8 calls/min**;
- the picture-mode select polled every 30 s with **no power gate**;
- the media player's ST read was already throttled (10 s) and already
  local-WS-primary — the smallest contributor.

At ~37/min that is **~53,000 calls/day per TV**, most of it redundant.

## The change (8.3.0)

- **Local WebSocket is primary.** Power/app/volume/mute keep polling locally
  every 5 s; SmartThings is only hit for the cloud-only fields.
- **Throttled ST cadence.** SmartThings is polled at a configurable interval
  while the TV is **ON** (default **30 s**, option *SmartThings poll interval
  when on*), and at a fixed **30 s keepalive** otherwise. On the local
  WebSocket coming up (power-on edge) one poll is forced immediately so
  cloud-only fields refresh without waiting for the interval.
- **Power sensors share one call.** The five power/energy sensors now read from
  a single shared coordinator that makes **one** `get_device_status` per cycle
  and **skips entirely while the TV is off** — but keeps polling when the Frame
  is showing **Art** (it still draws power), so art-mode consumption stays
  visible.
- **Picture-mode select and child light sensors are power-gated** and throttled
  to the same cadence.

Net effect on a realistic 6 h-on / 18 h-off day: roughly **~53,000 → ~7,500
calls/day per TV (~86% fewer)**, with the biggest savings while the TV is off.

## Tuning

*Settings → Devices & Services → SamsungTV Smart → Configure → (enable advanced
options) → **SmartThings poll interval when on***. Lower it (min 5 s) for
snappier channel/picture-mode updates at higher API cost; raise it (max 600 s)
to minimise calls. Changing it reloads the integration so the new cadence takes
effect. The off-state keepalive is fixed at 30 s.
