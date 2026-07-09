/*
 * Optimize the rendered source assets into the shipped formats.
 *
 *   .asset-src/scenes/<name>/overlays/*.png -> public/assets/scenes/<name>/beat_NN.webp
 *                             manifest.json -> copied with overlay paths rewritten
 *                             poster.png    -> poster.avif + poster.webp (halved)
 *   .asset-src/plates/*.png                 -> public/assets/plates/*.{avif,webp}
 *   .asset-src/cards/*.png                  -> public/assets/cards/*.webp (alpha kept)
 *   .asset-src/motion/*.gif                 -> public/assets/motion/*.webp (animated)
 *                                              + *-still.webp (first frame)
 *
 * The overlay alpha channel IS the emissive signal (alpha = luminance of the
 * rendered ink); it is preserved exactly. Fails the build if budgets are blown.
 *
 * Usage: node scripts/generate-assets.mjs .asset-src public/assets
 */
import { promises as fs } from "node:fs";
import path from "node:path";
import sharp from "sharp";

const [, , srcArg = ".asset-src", outArg = "public/assets"] = process.argv;
const SRC = path.resolve(srcArg);
const OUT = path.resolve(outArg);

const BUDGETS = {
  perSceneKB: 400, // all beats + manifest for one act
  totalMB: 3.5, // everything under public/assets
};

const MOTION_KEEP = ["wake_and_aurora", "save_moment", "promise_shatter", "prism_bloom"];

const report = [];

async function outSize(dir) {
  let total = 0;
  for (const e of await fs.readdir(dir, { withFileTypes: true, recursive: true })) {
    if (e.isFile()) total += (await fs.stat(path.join(e.parentPath, e.name))).size;
  }
  return total;
}

async function scenes() {
  const sceneRoot = path.join(SRC, "scenes");
  for (const name of (await fs.readdir(sceneRoot)).sort()) {
    const src = path.join(sceneRoot, name);
    const out = path.join(OUT, "scenes", name);
    await fs.mkdir(out, { recursive: true });

    const manifest = JSON.parse(await fs.readFile(path.join(src, "manifest.json"), "utf8"));
    for (const beat of manifest.beats) {
      const webpName = `${beat.id}.webp`;
      await sharp(path.join(src, beat.overlay))
        .webp({ quality: 90, alphaQuality: 100, effort: 6 })
        .toFile(path.join(out, webpName));
      beat.overlay = webpName;
    }
    await fs.writeFile(path.join(out, "manifest.json"), JSON.stringify(manifest));

    const poster = sharp(path.join(src, "poster.png")).resize({ width: 810 });
    await poster.clone().avif({ quality: 50 }).toFile(path.join(out, "poster.avif"));
    await poster.clone().webp({ quality: 70 }).toFile(path.join(out, "poster.webp"));

    const kb = (await outSize(out)) / 1024;
    report.push([`scenes/${name}`, kb]);
    if (kb > BUDGETS.perSceneKB) {
      throw new Error(`scene ${name} is ${kb.toFixed(0)}KB > ${BUDGETS.perSceneKB}KB budget`);
    }
  }
}

async function plates() {
  const src = path.join(SRC, "plates");
  const out = path.join(OUT, "plates");
  await fs.mkdir(out, { recursive: true });
  for (const f of (await fs.readdir(src)).sort()) {
    if (!f.endsWith(".png")) continue;
    const base = f.replace(/\.png$/, "");
    const img = sharp(path.join(src, f));
    await img.clone().avif({ quality: 45 }).toFile(path.join(out, `${base}.avif`));
    await img.clone().webp({ quality: 62 }).toFile(path.join(out, `${base}.webp`));
  }
  report.push(["plates", (await outSize(out)) / 1024]);
}

async function cards() {
  const src = path.join(SRC, "cards");
  const out = path.join(OUT, "cards");
  await fs.mkdir(out, { recursive: true });
  for (const f of (await fs.readdir(src)).sort()) {
    if (!f.endsWith(".png")) continue;
    await sharp(path.join(src, f))
      .webp({ quality: 90, alphaQuality: 100, effort: 6 })
      .toFile(path.join(out, f.replace(/\.png$/, ".webp")));
  }
  report.push(["cards", (await outSize(out)) / 1024]);
}

async function motion() {
  const src = path.join(SRC, "motion");
  const out = path.join(OUT, "motion");
  await fs.mkdir(out, { recursive: true });
  for (const name of MOTION_KEEP) {
    const gif = path.join(src, `${name}.gif`);
    await sharp(gif, { animated: true })
      .webp({ quality: 80, effort: 6, loop: 0 })
      .toFile(path.join(out, `${name}.webp`));
    await sharp(gif) // first frame only
      .webp({ quality: 80 })
      .toFile(path.join(out, `${name}-still.webp`));
  }
  report.push(["motion", (await outSize(out)) / 1024]);
}

async function og() {
  // Social card: the Veritas poster moment, center-cropped to 1200x630.
  await sharp(path.join(SRC, "scenes", "veritas", "poster.png"))
    .resize(1200, 630, { fit: "cover", position: "attention" })
    .jpeg({ quality: 82, mozjpeg: true })
    .toFile(path.join(OUT, "og.jpg"));
  report.push(["og.jpg", (await fs.stat(path.join(OUT, "og.jpg"))).size / 1024]);
}

await fs.mkdir(OUT, { recursive: true });
await scenes();
await plates();
await cards();
await motion();
await og();

const totalKB = report.reduce((a, [, kb]) => a + kb, 0);
console.log("\nasset budget");
for (const [k, kb] of report) console.log(`  ${k.padEnd(24)} ${kb.toFixed(0).padStart(6)} KB`);
console.log(`  ${"total".padEnd(24)} ${totalKB.toFixed(0).padStart(6)} KB`);
if (totalKB / 1024 > BUDGETS.totalMB) {
  throw new Error(`total assets ${(totalKB / 1024).toFixed(2)}MB > ${BUDGETS.totalMB}MB budget`);
}
