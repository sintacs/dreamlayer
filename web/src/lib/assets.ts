// Single-file builds (scripts/build-artifact.mjs) embed every asset as a data
// URI and expose them on window; the normal build leaves these globals unset
// and URLs resolve over the network as usual.

declare global {
  interface Window {
    __ASSET_MAP?: Record<string, string>;
    __MANIFESTS?: Record<string, unknown>;
  }
}

export function assetUrl(path: string): string {
  return window.__ASSET_MAP?.[path] ?? path;
}
