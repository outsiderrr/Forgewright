# Vendored third-party assets

`mermaid.min.js` is the upstream Mermaid v10.9.1 minified bundle, vendored
per ADR-025 / v1.0 F17 so the review UI keeps rendering graphs even when
the jsDelivr CDN is unreachable.

  * Source: <https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js>
  * Upstream: <https://github.com/mermaid-js/mermaid>
  * License: MIT (see upstream `LICENSE`)
  * Size: 3,335,717 bytes
  * SHA-256: `61b335a46df05a7ce1c98378f60e5f3e77a7fb608a1056997e8a649304a936d6`

## Refresh procedure

```bash
curl -fL --retry 3 --max-time 180 \
  -o tools/review_ui/static/vendor/mermaid.min.js \
  https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js
# verify the file ends in `;\n` — truncated downloads end mid-statement
tail -c 2 tools/review_ui/static/vendor/mermaid.min.js
# update size + SHA-256 above to match the new download:
shasum -a 256 tools/review_ui/static/vendor/mermaid.min.js
wc -c tools/review_ui/static/vendor/mermaid.min.js
# bump the CDN URL in tools/review_ui/static/app.js to the same version:
#   await loadScript('https://cdn.jsdelivr.net/npm/mermaid@<NEW>/dist/mermaid.min.js');
```

The frontend (`app.js`) tries this bundle first; on load failure or
missing global it falls back to the **same pinned version** on the
jsDelivr CDN (review C-5.1 — fallback shouldn't drift to a different
mermaid release between A-phase screenshots and B-phase replay), then
to the DOT/ASCII text representations (T-2.8 graph_views triple).
