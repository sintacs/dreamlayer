/** The connection state machine: three honest truths with hysteresis —
 * one blip is not an outage; one success is an instant recovery; coming
 * back fires the reconnect listeners (the outbox drains there). */
import { OFFLINE_AFTER, useConnectionStore } from "../state/useConnectionStore";

const conn = () => useConnectionStore.getState();

beforeEach(() => {
  useConnectionStore.setState({
    state: "unpaired",
    consecutiveFailures: 0,
    lastChangeTs: 0,
  });
});

describe("useConnectionStore", () => {
  it("starts unpaired and renders no scary label", () => {
    expect(conn().state).toBe("unpaired");
    expect(conn().label()).toBe("No Brain paired");
  });

  it("lan and relay report distinct truths", () => {
    conn().noteLan();
    expect(conn().state).toBe("lan");
    expect(conn().label()).toContain("home");
    conn().noteRelay();
    expect(conn().state).toBe("relay");
    expect(conn().label()).toContain("relay");
  });

  it("one blip is not an outage (hysteresis)", () => {
    conn().noteLan();
    conn().noteFailure();
    expect(conn().state).toBe("lan");          // still standing
    for (let i = 1; i < OFFLINE_AFTER; i++) conn().noteFailure();
    expect(conn().state).toBe("offline");
    expect(conn().label()).toContain("still remembering locally");
  });

  it("a single success recovers instantly", () => {
    conn().noteLan();
    for (let i = 0; i < OFFLINE_AFTER; i++) conn().noteFailure();
    expect(conn().state).toBe("offline");
    conn().noteLan();
    expect(conn().state).toBe("lan");
    expect(conn().consecutiveFailures).toBe(0);
  });

  it("reconnect listeners fire on the down→up edge only", () => {
    const seen: string[] = [];
    const off = conn().onReconnect((s) => seen.push(s));
    conn().noteLan();                          // unpaired→lan: was down → fires
    conn().noteLan();                          // lan→lan: no edge
    for (let i = 0; i < OFFLINE_AFTER; i++) conn().noteFailure();
    conn().noteRelay();                        // offline→relay: fires
    expect(seen).toEqual(["lan", "relay"]);
    off();
  });

  it("unpaired never counts as offline", () => {
    conn().noteUnpaired();
    conn().noteFailure();
    conn().noteFailure();
    expect(conn().state).toBe("unpaired");
  });
});
