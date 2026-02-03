/**
 * Global cache for Lottie animation data.
 * Prevents re-fetching on every component mount.
 */

type LottieData = object | null;

interface LottieCache {
  light: LottieData;
  dark: LottieData;
  loading: boolean;
  loaded: boolean;
}

const cache: LottieCache = {
  light: null,
  dark: null,
  loading: false,
  loaded: false,
};

const listeners: Set<() => void> = new Set();

function notifyListeners() {
  listeners.forEach((listener) => listener());
}

/**
 * Load Lottie data if not already cached.
 * Safe to call multiple times - only fetches once.
 */
export async function loadLottieData(): Promise<void> {
  if (cache.loaded || cache.loading) return;

  cache.loading = true;

  try {
    const [lightRes, darkRes] = await Promise.all([
      fetch("/brand/crux-spin.json"),
      fetch("/brand/crux-spin-reversed.json"),
    ]);

    const [light, dark] = await Promise.all([
      lightRes.json(),
      darkRes.json(),
    ]);

    cache.light = light;
    cache.dark = dark;
    cache.loaded = true;
  } catch {
    // Silently fail - components will use fallback spinner
  } finally {
    cache.loading = false;
    notifyListeners();
  }
}

/**
 * Get cached Lottie data for the given theme.
 */
export function getLottieData(theme: "light" | "dark"): LottieData {
  return theme === "dark" ? cache.dark : cache.light;
}

/**
 * Check if Lottie data is loaded.
 */
export function isLottieLoaded(): boolean {
  return cache.loaded;
}

/**
 * Subscribe to cache updates.
 * Returns unsubscribe function.
 */
export function subscribeLottieCache(callback: () => void): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}
