# DreamLayer — landing page

A single-file, scroll-driven marketing page for DreamLayer, redesigned as a
**Mac OS 8.1 "Platinum" desktop**: the page boots ("Welcome to DreamLayer",
barber-pole progress, extension icons marching in), lands on a dithered
desktop with a real menu bar (working pull-downs, live clock), and every
section lives in a period-accurate Platinum window — pinstriped title bars,
hard bevels, WindowShade collapsing (the lenses and the FAQ), a system-alert
Privacy Veil scene, desktop icons that zoom-rect out to the other pages, and
an "About This Layer" homage to About This Computer (menu → About).

Everything between the pixels is modern: Lenis smooth scroll driven from a
single GSAP ticker (`lenis.on('scroll', ScrollTrigger.update)`, no competing
RAF loops), scrubbed window choreography, retina-crisp hairlines, and full
`prefers-reduced-motion` fallbacks. The live product demos are unchanged —
the hero field is the JavaScript port of `DreamCanvas.tsx`, the "See it
move" orbs are live `<canvas>` re-creations of the shipping renderer's
motion, and the hero / capabilities / simulator glasses run the in-browser
Halo engine (`assets/sim/halo-sim.js`).

Chrome type is **ChicagoFLF** (public domain), copy is **Space Grotesk**
(OFL) — both self-hosted in `assets/fonts/`, so the page makes **zero
external requests** and works fully offline.

## Serve

No build step. Any static host:

```bash
cd landing && python3 -m http.server 8080    # open http://localhost:8080
```

## Assets

Everything in `assets/` is derived from this repo:

| Asset | Source |
|---|---|
| `hud/*.png` | verbatim copies of `assets/hud/samples/` — Meridian Solid renderer output, 256 px, one eye (the film-strip window, the Privacy Veil backdrop, and the boot "extensions") |
| `software/phone_*.png` | downscaled copies of `docs/gitbook/assets/phone/` — real iOS-app screenshots |
| `software/mac_panel.png` | a cropped, downscaled slice of `docs/gitbook/assets/panel/panel_full.png` — the Mac Brain control panel |
| `fonts/` | self-hosted ChicagoFLF (public domain) + Space Grotesk (OFL) — see `fonts/README.md` |

The "See it move" orbs and the walkthrough are **not** videos — they're live
`<canvas>` animations drawn in JS (`data-hud="horizon|recall|saved|walk"`),
reusing the app's own motion. This avoids the iOS Low-Power-Mode autoplay
block that stops `<video>`. All motion respects `prefers-reduced-motion`,
and the boot sequence is skippable (any input) and remembered per session.
