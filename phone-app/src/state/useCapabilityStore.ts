/**
 * useCapabilityStore — the phone's view of the Brain's optional-capability
 * catalog (INNOVATION_SESSION Category 8 #10 / B3).
 *
 * The Brain already serves the live catalog at GET /dreamlayer/capabilities
 * (host-python/src/dreamlayer/capabilities.py, consumed by the Mac panel). This
 * store fetches it from the paired Mac Brain and turns the 58-entry table into a
 * visible upgrade path: "your Brain can also learn to recognize speakers ▸
 * translate offline ▸ dream-train nightly". The phone never installs anything —
 * that happens on the Mac (a sealed bundle can't pip into itself); the phone
 * shows the path and which profile switches it on.
 *
 * State strings mirror capabilities.py:state() — active | off | missing |
 * unsupported | external. "missing" is the learnable set (an extra away).
 */
import { create } from "zustand";

import { useBrainStore } from "./useBrainStore";

export type CapItem = {
  key: string;
  tier: string;
  title: string;
  state: "active" | "off" | "missing" | "unsupported" | "external" | string;
  gain: string;
  impact: number;
  profiles: string[];
  extra: string | null;
};

type CapState = {
  items: CapItem[];
  summary: Record<string, number>;
  loaded: boolean;
  loading: boolean;
  error: string | null;
  connected: boolean;
  load: (fetchImpl?: typeof fetch) => Promise<void>;
  /** The upgrade path: not-yet-installed capabilities, best gain first. */
  learnable: () => CapItem[];
  activeCount: () => number;
};

export const useCapabilityStore = create<CapState>((set, get) => ({
  items: [],
  summary: {},
  loaded: false,
  loading: false,
  error: null,
  connected: false,

  load: async (fetchImpl: typeof fetch = fetch) => {
    const mac = useBrainStore.getState().macMini;
    if (!mac || !mac.url) {
      set({ connected: false, loaded: true, items: [], error: null });
      return;
    }
    set({ loading: true, error: null, connected: true });
    try {
      const base = mac.url.replace(/\/$/, "");
      const res = await fetchImpl(`${base}/dreamlayer/capabilities`, {
        headers: mac.token ? { Authorization: `Bearer ${mac.token}` } : {},
      });
      const data = await res.json();
      set({
        items: Array.isArray(data.items) ? (data.items as CapItem[]) : [],
        summary: (data.summary as Record<string, number>) || {},
        loaded: true,
        loading: false,
      });
    } catch (e: unknown) {
      // local UI stays usable; a failed fetch just leaves the last known list
      set({ error: e instanceof Error ? e.message : String(e), loading: false, loaded: true });
    }
  },

  learnable: () =>
    get()
      .items.filter((c) => c.state === "missing")
      .sort((a, b) => b.impact - a.impact),

  activeCount: () => get().items.filter((c) => c.state === "active").length,
}));
