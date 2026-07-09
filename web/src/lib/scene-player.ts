import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import type { SceneManifest } from "./manifest";
import { assetUrl } from "./assets";

export type ActMode = "scrub" | "autoplay";

// How much scroll one storyboard second costs in scrub mode. ~260px/s pins a
// 13s act for about 2.5 viewport-heights: long enough to read, short enough
// to never trap.
const PX_PER_SECOND = 260;

// The renderer's own dy drift is 1.5% of frame height; relative to a beat that
// is ~52% of frame width (square), that is ~5% of the element's height.
const DRIFT_Y_PERCENT = 5;

function createBeatElements(frame: HTMLElement, scene: string, manifest: SceneManifest): HTMLImageElement[] {
  // The manifest positions assume a clean 9:16 frame. On portrait screens the
  // lower quarter belongs to the copy overlay, so low-hanging beats (spoken
  // captions at y=0.82) lift to stay readable above it.
  const portrait = window.matchMedia("(max-aspect-ratio: 1/1)").matches;
  return manifest.beats.map((beat) => {
    const img = new Image();
    img.src = assetUrl(`assets/scenes/${scene}/${beat.overlay}`);
    img.alt = "";
    img.loading = "lazy";
    img.decoding = "async";
    img.className = "beat";
    const anchorY = portrait ? Math.min(beat.anchor[1], 0.62) : beat.anchor[1];
    img.style.left = `${beat.anchor[0] * 100}%`;
    img.style.top = `${anchorY * 100}%`;
    img.style.width = `${beat.width * 100}%`;
    img.style.willChange = "transform, opacity";
    frame.appendChild(img);
    return img;
  });
}

/**
 * Turn one demo manifest into a living act.
 *
 * Timeline seconds equal manifest seconds, so the site plays the exact edit
 * the demo tool exports. Each beat arrives with the renderer's own ease:
 * ease-out-cubic fade while settling from 0.94 scale and drifting up.
 *
 * "scrub" pins the section and plays the edit against scroll; "autoplay"
 * plays it on a clock, looping, whenever the act is on screen — for
 * environments where the document itself cannot scroll (host iframes).
 */
export function buildAct(section: HTMLElement, manifest: SceneManifest, mode: ActMode): void {
  const scene = section.dataset.scene!;
  const frame = section.querySelector<HTMLElement>(".stage-frame")!;
  const plate = section.querySelector<HTMLElement>(".stage-plate")!;
  const beatEls = createBeatElements(frame, scene, manifest);

  const tl = gsap.timeline(
    mode === "scrub"
      ? {
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: section,
            start: "top top",
            end: `+=${Math.round(manifest.duration * PX_PER_SECOND)}`,
            pin: true,
            scrub: 0.6,
            anticipatePin: 1,
          },
        }
      : { defaults: { ease: "none" }, paused: true, repeat: -1, repeatDelay: 1.6 }
  );

  // The world drifts a touch while the act plays: depth without a single
  // layout property.
  gsap.set(plate, { scale: 1.06, transformOrigin: "50% 50%" });
  if (mode === "scrub") {
    tl.fromTo(plate, { yPercent: 1.6 }, { yPercent: -1.6, duration: manifest.duration }, 0);
  } else {
    // Looping timeline: breathe the plate instead so the repeat never snaps.
    gsap.fromTo(
      plate,
      { yPercent: 1.2 },
      { yPercent: -1.2, duration: manifest.duration, ease: "sine.inOut", yoyo: true, repeat: -1 }
    );
  }

  for (const [i, beat] of manifest.beats.entries()) {
    const el = beatEls[i];
    const fade = Math.max(beat.fade, 0.001);
    tl.fromTo(
      el,
      { autoAlpha: 0, scale: 0.94, yPercent: DRIFT_Y_PERCENT },
      { autoAlpha: 1, scale: 1, yPercent: 0, duration: fade, ease: "cubic.out" },
      beat.t_in
    );
    const outAt = mode === "autoplay" ? Math.min(beat.t_out, manifest.duration) : beat.t_out;
    if (outAt < manifest.duration || mode === "autoplay") {
      tl.to(el, { autoAlpha: 0, duration: fade, ease: "power1.in" }, outAt - fade);
    }
  }

  // Copy lines arrive with the beats they narrate; the previous line steps
  // back. Opacity only — the text never leaves the accessibility tree.
  const lines = Array.from(section.querySelectorAll<HTMLElement>(".act-lines p"));
  lines.forEach((line, i) => {
    const t = Number(line.dataset.t ?? 0);
    tl.fromTo(line, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.45, ease: "cubic.out" }, t);
    if (i > 0) {
      tl.to(lines[i - 1], { opacity: 0, y: -10, duration: 0.35, ease: "power1.in" }, t - 0.1);
    }
  });
  if (mode === "autoplay" && lines.length > 0) {
    // Rest the last line before the loop rolls again.
    tl.to(lines[lines.length - 1], { opacity: 0, duration: 0.4, ease: "power1.in" }, manifest.duration - 0.4);
  }

  if (mode === "autoplay") {
    new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) tl.play();
          else tl.pause();
        }
      },
      { threshold: 0.35 }
    ).observe(section);
  }
}

export { gsap, ScrollTrigger };
