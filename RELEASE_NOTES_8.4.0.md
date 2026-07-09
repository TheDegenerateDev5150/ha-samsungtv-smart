# Release notes — 8.4.0

If this project is useful to you, you can support its development:

# <a href="https://buymeacoffee.com/thefab21" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-black.png" alt="Buy Me A Coffee" height="41" width="174"></a>

## Artwork identification (opt-in) — engine + manual service (8.4.0b1)

New optional feature: identify the artwork currently shown on a Frame TV, so
Home Assistant can display its title, artist, date and a short artist bio.

**How it works** — two stages, cache-first:
1. **Reverse image search** (Google Cloud Vision *Web Detection*) turns the
   thumbnail into concrete candidate titles/artists from the real web.
2. **LLM confirmation** (Anthropic, OpenAI *or* Gemini) is handed those candidates and
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
  the LLM provider (Anthropic/OpenAI/Gemini), paste its key, optionally set a
  model (blank = `claude-haiku-4-5` / `gpt-4o` / `gemini-2.5-flash`), and
  choose whether to also identify
  personal photos (off by default — they're rarely in the art index). Keys are
  stored in the config entry (never in your YAML/Git).
- Call **`samsungtv_smart.art_identify`** on the TV entity (a `Response
  variable` returns the metadata; `force: true` bypasses the cache).

Costs are tiny: Google Vision is free under ~1000 requests/month, and — since
the same few dozen artworks rotate — the cache serves almost everything after a
short warm-up, so the LLM is rarely called.

## Automatic identification + metadata sensor (8.4.0b2)

When the feature is enabled, a new **`sensor.<tv>_art_metadata`** is created. It
watches the artwork on screen and, on every change (debounced ~8 s so a fast
slideshow doesn't fire per frame), runs the pipeline automatically and
publishes:

- **state** = the artwork title (or `Unidentified`);
- **attributes** = `artist`, `date`, `artist_biography`, `artwork_description`,
  `visual_description`, `confidence`, `matched_candidate`,
  `suggested_search_query`, `source` (`cache`/`fresh`), `content_id`.

The sensor and the manual `art_identify` service share one cache, so a title
seen once is instant (and free) forever after. Enabling/disabling the feature
adds/removes this sensor (a reload); editing an API key does not reload.

### Ready-made Lovelace card

A Markdown card that shows the current artwork thumbnail with its title, artist
and bio underneath (replace `samsung_hacs` with your entity):

```yaml
type: markdown
content: >
  {% set m = 'sensor.samsung_hacs_art_metadata' %}
  {% set thumb = state_attr('sensor.samsung_hacs_frame_art', 'current_thumbnail_url') %}
  {% if thumb %}![art]({{ thumb }}){% endif %}


  {% if is_state_attr(m, 'identified', true) %}
  ## {{ states(m) }}

  **{{ state_attr(m, 'artist') }}** · {{ state_attr(m, 'date') }}


  {{ state_attr(m, 'artist_biography') }}
  {% else %}
  _Artwork not identified_
  {% endif %}
```

A richer `custom:button-card` / picture-glance version can be built if wanted.

### Troubleshooting (8.4.0b3)

Debug logging now traces the whole pipeline — the gating decision, the
thumbnail read, the **Vision candidates**, the **raw LLM reply**, cache
hit/miss, timing, and each sensor trigger. Enable it with:

```yaml
logger:
  logs:
    custom_components.samsungtv_smart.art_identify: debug
    custom_components.samsungtv_smart.sensor: debug
```

Typical lines: `Vision candidates best_guess=[…]`, `LLM (anthropic/…) raw
reply: {…}`, `identified=True title=… in 6.3s`, `cache HIT (…)`.
