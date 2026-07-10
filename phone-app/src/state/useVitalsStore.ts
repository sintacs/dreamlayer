/**
 * useVitalsStore — give device telemetry an audience (INNOVATION_SESSION Cat 8 #5 / B11).
 *
 * The glasses dutifully emit TEL frames (halo-lua/ble/telemetry.lua):
 *   { t: "TEL", event, ts, payload }
 * where event ∈ CARD_SHOWN | CARD_DISMISSED | PRIVACY_VEIL | PRIVACY_RESUMED |
 * TICK_ERROR | HEAP | FIGMENT_BANISHED. HaloBridge already routes them to an
 * onTelemetry callback that nobody registered. This store IS that audience: it
 * folds the stream into device vitals the "Device Vitals" screen renders.
 */
import { create } from "zustand";

const HEAP_CAP = 60; // ~1 hour of once-a-minute watermarks

type VitalsState = {
  heap: number[];
  lastHeapKb: number | null;
  crashes: number;
  lastError: string | null;
  shown: number;
  dismissed: number;
  banished: number;
  veiled: boolean;
  events: number;
  ingest: (tel: Record<string, unknown>) => void;
  dismissRate: () => number;
  reset: () => void;
};

const EMPTY = {
  heap: [] as number[],
  lastHeapKb: null as number | null,
  crashes: 0,
  lastError: null as string | null,
  shown: 0,
  dismissed: 0,
  banished: 0,
  veiled: false,
  events: 0,
};

export const useVitalsStore = create<VitalsState>((set, get) => ({
  ...EMPTY,

  ingest: (tel) => {
    const ev = String(tel.event || "");
    const p = (tel.payload || {}) as Record<string, unknown>;
    switch (ev) {
      case "HEAP": {
        const kb = Number(p.kb);
        if (Number.isFinite(kb)) {
          set((s) => ({ heap: [...s.heap, kb].slice(-HEAP_CAP), lastHeapKb: kb }));
        }
        break;
      }
      case "TICK_ERROR":
        set((s) => ({
          crashes: typeof p.count === "number" ? (p.count as number) : s.crashes + 1,
          lastError: p.error != null ? String(p.error) : s.lastError,
        }));
        break;
      case "CARD_SHOWN":
        set((s) => ({ shown: s.shown + 1 }));
        break;
      case "CARD_DISMISSED":
        set((s) => ({ dismissed: s.dismissed + 1 }));
        break;
      case "FIGMENT_BANISHED":
        set((s) => ({ banished: s.banished + 1 }));
        break;
      case "PRIVACY_VEIL":
        set({ veiled: true });
        break;
      case "PRIVACY_RESUMED":
        set({ veiled: false });
        break;
      default:
        break;
    }
    set((s) => ({ events: s.events + 1 }));
  },

  dismissRate: () => {
    const s = get();
    return s.shown ? s.dismissed / s.shown : 0;
  },

  reset: () => set({ ...EMPTY }),
}));
