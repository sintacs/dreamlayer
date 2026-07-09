import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/sections.css";
import "./lib/assets";
import { initWaitlist } from "./waitlist";
import { initDreamField } from "./lib/dreamfield";

initWaitlist();

// The hero's living sky runs in every mode (it draws a single still frame
// under reduced motion) — the page breathes even where scroll effects can't.
const heroStage = document.querySelector<HTMLElement>(".hero .stage");
const field = document.querySelector<HTMLCanvasElement>("#dreamfield");
if (heroStage && field) initDreamField(field, heroStage);

// Total reduced-motion contract, mirroring the product's own: the page is a
// calm static document — every scene shows its hold pose, nothing pins,
// nothing scrubs, ambient loops show stills.
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Two live modes. "scrub": pinned acts play against scroll (the cinematic
// desktop cut). "autoplay": each act plays its real manifest timeline on a
// clock when it enters view — for embedded touch contexts (artifact hosts
// render the page in an iframe that often cannot scroll internally on iOS)
// and anywhere the document lays out with no internal scroll range.
function chooseMode(): "scrub" | "autoplay" {
  const embedded = typeof window.__ASSET_MAP !== "undefined" && window.self !== window.top;
  const touch = window.matchMedia("(pointer: coarse)").matches;
  const unscrollable = document.documentElement.scrollHeight <= window.innerHeight * 1.5;
  return unscrollable || (embedded && touch) ? "autoplay" : "scrub";
}

if (!reduceMotion) {
  const start = (): void => {
    const mode = chooseMode();
    import("./motion").then((m) => m.boot(mode));
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
}
