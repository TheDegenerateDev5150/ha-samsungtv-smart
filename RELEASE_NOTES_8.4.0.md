# Release notes — 8.4.0

If this project is useful to you, you can support its development:

# <a href="https://buymeacoffee.com/thefab21" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-black.png" alt="Buy Me A Coffee" height="41" width="174"></a>

## Artwork identification (opt-in) — engine + manual service (8.4.0b1)

New optional feature: identify the artwork currently shown on a Frame TV, so
Home Assistant can display its title, artist, date and a short artist bio.

**How it works** — two stages, cache-first:
1. **Reverse image search** (Google Cloud Vision *Web Detection*) turns the
   thumbnail into concrete candidate titles/artists from the real web.
2. **LLM confirmation** (Anthropic *or* OpenAI) is handed those candidates and
   the image, and confirms only if one genuinely matches what it sees —
   otherwise it returns "not identified". Reverse-search-first is what stops
   the hallucinations a bare vision model produces on obscure works.

Results are **cached** so each artwork is identified only once — keyed by the
Samsung Art-Store id (`SAM-*`, stable across TV resets) or, for personal
uploads, by the image content itself (so a recycled local id can never surface
another image's metadata). Successful identifications are kept indefinitely;
"not identified" is retried after two weeks; transport errors are never cached.

**This build (b1) ships the engine + configuration + a manual service** so it
can be tested end-to-end before the automatic per-artwork trigger and the
metadata sensor land:

- Configure under **Settings → Devices → the TV → Configure → Art
  Identification**: enable the feature, paste your Google Vision API key, pick
  the LLM provider (Anthropic/OpenAI), paste its key, optionally set a model
  (blank = `claude-haiku-4-5` / `gpt-4o`), and choose whether to also identify
  personal photos (off by default — they're rarely in the art index). Keys are
  stored in the config entry (never in your YAML/Git).
- Call **`samsungtv_smart.art_identify`** on the TV entity (a `Response
  variable` returns the metadata; `force: true` bypasses the cache).

Costs are tiny: Google Vision is free under ~1000 requests/month, and — since
the same few dozen artworks rotate — the cache serves almost everything after a
short warm-up, so the LLM is rarely called.

_Coming next: automatic identification on every artwork change + a
`sensor.<tv>_art_metadata` (title as state; artist/date/bio/confidence as
attributes) + a ready-made Lovelace card._
