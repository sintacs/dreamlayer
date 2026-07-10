/** In-memory AsyncStorage for jest — the same three calls the app uses. */
const store = new Map<string, string>();

export default {
  async getItem(key: string): Promise<string | null> {
    return store.has(key) ? (store.get(key) as string) : null;
  },
  async setItem(key: string, value: string): Promise<void> {
    store.set(key, value);
  },
  async removeItem(key: string): Promise<void> {
    store.delete(key);
  },
  /** test helper */
  __reset(): void {
    store.clear();
  },
};
