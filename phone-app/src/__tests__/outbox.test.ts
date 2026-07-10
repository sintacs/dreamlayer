/** The config outbox: a toggle flipped in a tunnel still lands. Failed
 * pushes are merged + kept (never silently swallowed anymore), the UI can
 * see `unsynced()`, and the Brain coming back drains the queue. */
import { useBrainStore } from "../state/useBrainStore";
import { useConnectionStore } from "../state/useConnectionStore";

const brain = () => useBrainStore.getState();
const conn = () => useConnectionStore.getState();

function flushMicrotasks() {
  return new Promise((r) => setTimeout(r, 0));
}

beforeEach(() => {
  useBrainStore.setState({
    macMini: { connected: false, url: "", token: "", relayUrl: "" },
    cloud: true,
    incognito: false,
    outbox: {},
    demoMode: false,
  });
  useConnectionStore.setState({ state: "unpaired", consecutiveFailures: 0 });
  (global as any).fetch = jest.fn(() => Promise.reject(new Error("offline")));
});

describe("config outbox", () => {
  it("queues a switch change while unpaired", async () => {
    brain().setCloud(false);
    await flushMicrotasks();
    expect(brain().unsynced()).toBe(true);
    expect(brain().outbox).toMatchObject({ cloud_enabled: false });
    expect((global as any).fetch).not.toHaveBeenCalled();
  });

  it("keeps the patch when the Brain is unreachable", async () => {
    useBrainStore.setState({
      macMini: { connected: true, url: "http://10.0.0.9:7777", token: "t" },
    });
    brain().setIncognito(true);
    await flushMicrotasks();
    expect(brain().unsynced()).toBe(true);
    expect(brain().outbox).toMatchObject({ network_mode: "lan_only" });
  });

  it("merges patches: last write per key wins", async () => {
    brain().setCloud(false);
    await flushMicrotasks();
    brain().setCloud(true);
    await flushMicrotasks();
    expect(brain().outbox).toMatchObject({ cloud_enabled: true });
  });

  it("drains on the reconnect edge and clears unsynced", async () => {
    useBrainStore.setState({
      macMini: { connected: true, url: "http://10.0.0.9:7777", token: "t" },
    });
    brain().setCloud(false);
    await flushMicrotasks();
    expect(brain().unsynced()).toBe(true);

    // the Brain comes back: fetch succeeds now
    (global as any).fetch = jest.fn(() =>
      Promise.resolve({ json: async () => ({}) }));
    useConnectionStore.setState({ state: "offline" });
    conn().noteLan();                        // fires the reconnect listener
    await flushMicrotasks();
    expect(brain().unsynced()).toBe(false);
    // and the drain POSTed the merged patch to /dreamlayer/config
    const calls = ((global as any).fetch as jest.Mock).mock.calls;
    expect(calls.some(([url]) => String(url).endsWith("/dreamlayer/config"))).toBe(true);
  });

  it("summarize_emails rides the same outbox", async () => {
    brain().setSummarizeEmails(true);
    await flushMicrotasks();
    expect(brain().outbox).toMatchObject({ summarize_emails: true });
  });
});
