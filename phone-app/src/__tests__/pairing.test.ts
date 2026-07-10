/** The pairing codec — the first 60 seconds of every user's life with the
 * product, previously tested nowhere on the phone side. Byte-compatible
 * with host-python/src/dreamlayer/pairing.py. */
import { decodePairing, encodePairing, SCHEME } from "../services/pairing";

const BUNDLE = {
  brainUrl: "http://192.168.1.20:7777",
  token: "rune-birch",
  glassesId: "HALO-1A2B",
  label: "Studio",
  relayUrl: "https://relay.example.com",
};

describe("pairing codec", () => {
  it("roundtrips the full trio bundle", () => {
    expect(decodePairing(encodePairing(BUNDLE))).toEqual(BUNDLE);
  });

  it("roundtrips a brain-only bundle", () => {
    const b = { ...BUNDLE, glassesId: "", relayUrl: "", label: "DreamLayer" };
    expect(decodePairing(encodePairing(b))).toEqual(b);
  });

  it("accepts a code without the scheme prefix", () => {
    const code = encodePairing(BUNDLE).slice(SCHEME.length + 1);
    expect(decodePairing(code).token).toBe("rune-birch");
  });

  it("survives unicode labels (utf-8 path)", () => {
    const b = { ...BUNDLE, label: "café ✨" };
    expect(decodePairing(encodePairing(b)).label).toBe("café ✨");
  });

  it("throws on garbage rather than pairing to nonsense", () => {
    expect(() => decodePairing("dreamlayer:!!!not-base64!!!")).toThrow();
  });
});
