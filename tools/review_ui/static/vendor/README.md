# Vendored third-party assets

`mermaid.min.js` is the upstream Mermaid v10.9.1 minified bundle, vendored
per ADR-025 / v1.0 F17 so the review UI keeps rendering graphs even when
the jsDelivr CDN is unreachable.

  * Source: <https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js>
  * Upstream: <https://github.com/mermaid-js/mermaid>
  * License: MIT (see upstream `LICENSE`)
  * SHA pin: see file size + Mermaid release tag `v10.9.1`

## Refresh procedure

```bash
curl -fL --retry 3 --max-time 180 \
  -o tools/review_ui/static/vendor/mermaid.min.js \
  https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js
# verify the file ends in `;\n` — truncated downloads end mid-statement
tail -c 2 tools/review_ui/static/vendor/mermaid.min.js
```

The frontend (`app.js`) tries this bundle first; on load failure or
missing global it falls back to the same CDN URL, then to the DOT/ASCII
text representations (T-2.8 graph_views triple).
