// The demo renderer's EDL, produced by host-python/src/dreamlayer/demo/scene.py.

import "./assets";

export interface BeatSpec {
  id: string;
  overlay: string; // file name relative to the scene directory
  card_type: string;
  t_in: number; // seconds
  t_out: number; // seconds
  anchor: [number, number]; // fractional center on the 9:16 frame
  width: number; // fraction of frame width
  fade: number; // seconds
  label: string;
}

export interface SceneManifest {
  name: string;
  size: [number, number];
  fps: number;
  duration: number; // seconds
  blend: string; // "screen" — additive light over the plate
  note: string;
  beats: BeatSpec[];
}

export async function loadManifest(scene: string): Promise<SceneManifest> {
  const inline = window.__MANIFESTS?.[scene];
  if (inline) return inline as SceneManifest;
  const res = await fetch(`assets/scenes/${scene}/manifest.json`);
  if (!res.ok) throw new Error(`manifest for ${scene}: ${res.status}`);
  return res.json();
}
