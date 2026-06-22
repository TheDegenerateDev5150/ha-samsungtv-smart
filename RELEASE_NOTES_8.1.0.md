# Release notes — 8.1.0 (since 8.0.0)

> **Status: pre-release (beta).** 8.1.0 builds on the stable 8.0.0 three-channel
> rework with IP Control reliability and observability improvements.

---

## IP Control

- **Daily device-info refresh**: TV model and firmware version (learned via
  IP Control's `getDeviceInformation`) are now refreshed automatically every
  24h instead of only once at pairing time, so an OTA firmware upgrade is
  picked up without requiring a manual reconfigure.
- **REST port self-heal**: the REST client now honors the configured port and
  falls back between **8001 and 8002 at runtime** on a connection failure,
  persisting the working port — the same self-heal already in place for the
  Art channel (8.0.0) now also covers the REST/device-info path.

## Reliability & observability

- **Per-TV "slow update" warning**: when a poll cycle takes longer than the
  5s scan interval, the integration now logs its own host-tagged warning
  (`[192.168.x.y] Update took X.Xs, longer than the Xs scan interval`)
  instead of relying solely on Home Assistant's core scheduler warning, which
  cannot identify which TV/entity is responsible in a multi-TV setup.

---

## Known limitations / not yet validated

- Carries forward all 8.0.0 known limitations (see `RELEASE_NOTES_8.0.0.md`),
  including the *Enable IP Control Art Mode* firmware-safety warning.

---

*These notes were assembled from the 8.1.0 codebase (`v8.1-dev`, since the
8.0.0 release). If any 8.1.0bNN pre-release change is missing, add it under
the relevant section.*
