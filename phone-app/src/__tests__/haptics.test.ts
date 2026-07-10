/** The haptic vocabulary is a data table with rules — pin the rules. */
import { PATTERNS, play, playTinCan } from "../services/haptics";

describe("haptic vocabulary", () => {
  it("answer-ahead is silent by design", () => {
    expect(PATTERNS.answer_ahead).toHaveLength(0);
  });

  it("every pattern fits inside the 400ms pocket rule", () => {
    for (const [name, beats] of Object.entries(PATTERNS)) {
      for (const beat of beats) {
        expect({ name, at: beat.at }).toEqual({ name, at: expect.any(Number) });
        expect(beat.at).toBeLessThanOrEqual(400);
      }
    }
  });

  it("the veil is unique and directional", () => {
    const on = PATTERNS.veil_on.map((b: any) => b.impact);
    const off = PATTERNS.veil_off.map((b: any) => b.impact);
    expect(on).toEqual(["heavy", "medium", "light"]);   // descending: going dark
    expect(off).toEqual(["light", "medium", "heavy"]);  // ascending: eyes open
  });

  it("lens signatures never reuse system patterns", () => {
    const sig = (beats: any[]) => JSON.stringify(beats);
    const system = ["confirm", "action", "success", "warn", "notice",
                    "attention", "interrupt"] as const;
    const lenses = ["commitment_crack", "commitment_bloom", "truth_flag",
                    "figment_deployed"] as const;
    for (const lens of lenses) {
      for (const sys of system) {
        expect(sig(PATTERNS[lens])).not.toBe(sig(PATTERNS[sys]));
      }
    }
  });

  it("play() and playTinCan() never throw without the native module", () => {
    expect(() => play("interrupt")).not.toThrow();
    expect(() => playTinCan([0, 150, 300])).not.toThrow();
    expect(() => playTinCan([0, 1, 2, 3, 4, 5, 6, 7, 8])).not.toThrow(); // clamped
  });
});
