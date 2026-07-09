# Release notes — 8.3.3

If this project is useful to you, you can support its development:

# <a href="https://buymeacoffee.com/thefab21" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-black.png" alt="Buy Me A Coffee" height="41" width="174"></a>

## Picture mode — the option list now follows the active input (8.3.3b1, #116)

- **Fix: the Picture Mode dropdown could get stuck on the wrong input's modes.**
  Samsung's picture-mode list is **per-input** — a PC / Graphic source exposes
  only `Entertain` / `Graphic`, a normal source (TV, HDMI/AVR) exposes
  `Movie` / `Standard` / `Dynamic` / … The integration fetched
  `supportedPictureModes` **once at startup** and afterwards only *appended*
  newly-seen modes, so:
  - leaving the TV on a PC input, turning it off, then coming back on a normal
    input left the dropdown stuck on `Entertain` / `Graphic`;
  - selecting a valid mode on the remote *added* it to the list but kept the
    stale PC modes — producing a bogus **merged list of two source profiles**;
  - even restarting Home Assistant didn't clear it.
  This broke automations, since standard modes (`Movie`, `Standard`) were
  flagged as invalid choices for the active input.
- **The supported-mode list is now rebuilt from the cloud on every poll**
  (the data was already in the same response we fetch for the current mode, so
  there's no extra API call). When the active input changes, the dropdown
  follows within one SmartThings poll cycle — matching what the official
  SmartThings app shows. Stale modes from a previous input are dropped instead
  of accumulating.
