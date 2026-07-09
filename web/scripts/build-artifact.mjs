/*
 * Fold the built site into one self-contained HTML fragment for environments
 * that allow no external requests (e.g. Claude Artifacts): CSS and JS inlined,
 * every image a data URI, scene manifests injected as globals.
 *
 * Usage:  vite build --mode artifact && node scripts/build-artifact.mjs
 * Output: dist/dreamlayer-artifact.html
 *
 * The output is page *content* (no doctype/html/head/body), as artifact hosts
 * wrap it in their own document skeleton. AVIF <source> variants are dropped
 * (WebP fallbacks remain) to halve the embedded plate bytes.
 */
import { promises as fs } from "node:fs";
import path from "node:path";

const DIST = path.resolve("dist");

const MIME = {
  ".webp": "image/webp",
  ".jpg": "image/jpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

async function dataUri(rel) {
  const file = path.join(DIST, rel);
  const mime = MIME[path.extname(rel)];
  if (!mime) throw new Error(`no mime for ${rel}`);
  return `data:${mime};base64,${(await fs.readFile(file)).toString("base64")}`;
}

const html = await fs.readFile(path.join(DIST, "index.html"), "utf8");

// The single bundle and stylesheet vite emitted.
const jsFile = html.match(/src="\.\/(assets\/index-[^"]+\.js)"/)[1];
const cssFile = html.match(/href="\.\/(assets\/index-[^"]+\.css)"/)[1];
const css = await fs.readFile(path.join(DIST, cssFile), "utf8");
const js = (await fs.readFile(path.join(DIST, jsFile), "utf8")).replaceAll("</script>", "<\\/script>");

let body = html.match(/<body>([\s\S]*)<\/body>/)[1];

// Drop AVIF sources; the WebP siblings carry the artifact.
body = body.replace(/\s*<source[^>]*type="image\/avif"[^>]*\/?>/g, "");

// Embed every remaining asset reference.
const refs = new Set(body.match(/assets\/[\w./-]+\.(?:webp|jpg|png|svg)/g) ?? []);
for (const ref of refs) {
  body = body.replaceAll(ref, await dataUri(ref));
}

// Scene manifests and beat overlays, delivered as globals instead of fetches.
const manifests = {};
const assetMap = {};
const scenesDir = path.join(DIST, "assets/scenes");
for (const scene of await fs.readdir(scenesDir)) {
  const manifest = JSON.parse(await fs.readFile(path.join(scenesDir, scene, "manifest.json"), "utf8"));
  manifests[scene] = manifest;
  for (const beat of manifest.beats) {
    const rel = `assets/scenes/${scene}/${beat.overlay}`;
    assetMap[rel] = await dataUri(rel);
  }
}

const out = [
  // Artifact hosts wrap this fragment in their own skeleton, which may not
  // declare a mobile viewport; browsers honor the meta wherever it appears,
  // and without it phones lay the page out at 980px and shrink it.
  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />',
  "<title>DreamLayer</title>",
  `<style>\n${css}\n</style>`,
  body,
  `<script>window.__MANIFESTS=${JSON.stringify(manifests)};window.__ASSET_MAP=${JSON.stringify(assetMap)};</script>`,
  `<script type="module">\n${js}\n</script>`,
].join("\n");

const outPath = path.join(DIST, "dreamlayer-artifact.html");
await fs.writeFile(outPath, out);

// Verify the markup (not the JS bundle, which legitimately contains template
// strings) references nothing external.
const leftovers = body.match(/(?:src|href|srcset)="(?!data:|#|mailto:|https:\/\/github\.com)[^"]+"/g) ?? [];
console.log(`wrote ${outPath} (${(out.length / 1024 / 1024).toFixed(2)} MB)`);
if (leftovers.length) {
  console.error("non-inlined references remain:", leftovers);
  process.exit(1);
}
