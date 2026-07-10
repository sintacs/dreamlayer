/**
 * useConnectionStore — ONE truth about reachability, instead of a guess
 * per call.
 *
 * Before this store every fetch independently tried LAN then relay, so the
 * app had no idea whether the Brain was home, away, or gone — a StatusPill
 * could say "connected" while every request was quietly failing. Now every
 * Brain fetch reports its outcome here and the app renders three honest
 * states:
 *
 *   lan      "Brain: home"                     — direct LAN hit
 *   relay    "Brain: away — via relay"         — LAN missed, relay carried it
 *   offline  "Brain: unreachable — still remembering locally"
 *   unpaired no Brain configured at all
 *
 * Hysteresis: one failed request never flips the pill (radios blip) — it
 * takes OFFLINE_AFTER consecutive failures to go offline; a single success
 * recovers instantly. Transitions back to lan/relay fire the reconnect
 * listeners (the config outbox drains there).
 */
import { create } from "zustand";

export type ConnState = "lan" | "relay" | "offline" | "unpaired";

export const OFFLINE_AFTER = 2; // consecutive failures before we say offline

type Listener = (state: ConnState) => void;

type ConnectionState = {
  state: ConnState;
  lastChangeTs: number;
  consecutiveFailures: number;

  /** Human line for the UI — the three truths. */
  label: () => string;
  reachable: () => boolean;

  // outcome reports (brainFetch calls these)
  noteLan: () => void;
  noteRelay: () => void;
  noteFailure: () => void;
  noteUnpaired: () => void;

  /** Actively probe the Brain (status endpoint) and settle the state. */
  probe: (m: { url: string; token: string; relayUrl?: string }) => Promise<ConnState>;

  onReconnect: (fn: Listener) => () => void;
};

const listeners = new Set<Listener>();

function settle(
  set: (p: Partial<ConnectionState>) => void,
  get: () => ConnectionState,
  next: ConnState,
  resetFailures: boolean,
) {
  const prev = get().state;
  const wasDown = prev === "offline" || prev === "unpaired";
  set({
    state: next,
    ...(resetFailures ? { consecutiveFailures: 0 } : {}),
    ...(prev !== next ? { lastChangeTs: Date.now() } : {}),
  });
  if (wasDown && (next === "lan" || next === "relay")) {
    listeners.forEach((fn) => {
      try {
        fn(next);
      } catch {
        /* a listener must never break the machine */
      }
    });
  }
}

export const useConnectionStore = create<ConnectionState>((set, get) => ({
  state: "unpaired",
  lastChangeTs: Date.now(),
  consecutiveFailures: 0,

  label: () => {
    switch (get().state) {
      case "lan":
        return "Brain: home";
      case "relay":
        return "Brain: away — via relay";
      case "offline":
        return "Brain: unreachable — still remembering locally";
      default:
        return "No Brain paired";
    }
  },

  reachable: () => get().state === "lan" || get().state === "relay",

  noteLan: () => settle(set, get, "lan", true),
  noteRelay: () => settle(set, get, "relay", true),

  noteFailure: () => {
    const n = get().consecutiveFailures + 1;
    set({ consecutiveFailures: n });
    // hysteresis: a blip is not an outage
    if (n >= OFFLINE_AFTER && get().state !== "unpaired") {
      settle(set, get, "offline", false);
    }
  },

  noteUnpaired: () => settle(set, get, "unpaired", true),

  probe: async (m) => {
    if (!m.url) {
      get().noteUnpaired();
      return "unpaired";
    }
    const headers: Record<string, string> = m.token
      ? { "X-DreamLayer-Token": m.token }
      : {};
    try {
      await fetch(m.url + "/dreamlayer/status", { headers });
      get().noteLan();
      return "lan";
    } catch {
      if (m.relayUrl) {
        try {
          await fetch(m.relayUrl + "/dreamlayer/status", { headers });
          get().noteRelay();
          return "relay";
        } catch {
          /* fall through */
        }
      }
      get().noteFailure();
      return get().state;
    }
  },

  onReconnect: (fn) => {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
}));
