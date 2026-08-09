# Mode 3 — HTML mockup

Single-file HTML, only when explicitly asked ("mock this up in HTML," "show me the mockup," "HTML version"). Ambiguous ("can you mock this up")? Ask once: "Inline sketch (quick) or HTML mockup (opens in browser)?" After a mode-1 or mode-2 close, a multi-state or shareable design earns a short offer — "Want me to render this as an HTML mockup?" — never unsolicited production, never for tiny riffs.

When producing: semantic markup, inline CSS only (no CDN deps, no build step), medium fidelity, mobile-first CSS scaling up via `@media (min-width: ...)`. Palette: use the team's brand if documented (repo map / architect docs) or ask; no preference means neutral grays + a single accent, with the placeholder called out explicitly. Save as `<slug>.html` beside the spec in `<plans>/design/`. Need a PDF? Browser → Cmd+P → Save as PDF — Pixel doesn't ship a PDF pipeline.
