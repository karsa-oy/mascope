// happy-dom does not expose a global `localStorage` under the Node version we
// run, so provide a minimal in-memory implementation for unit tests. Stores
// that persist UI state (selection, split, darkmode) read `localStorage`
// directly; this makes those code paths exercisable without a browser.
if (typeof globalThis.localStorage === 'undefined' || !globalThis.localStorage?.clear) {
  const store = new Map()
  globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
    key: (index) => Array.from(store.keys())[index] ?? null,
    get length() {
      return store.size
    }
  }
}
