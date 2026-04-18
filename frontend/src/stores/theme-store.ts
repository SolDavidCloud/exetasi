import { defineStore } from 'pinia';
import { Dark } from 'quasar';
import { computed, ref, watch } from 'vue';

export type ThemeMode = 'auto' | 'light' | 'dark';

const STORAGE_KEY = 'exetasi:theme-mode';

function readStoredMode(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'auto';
  }
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === 'light' || raw === 'dark' || raw === 'auto') {
    return raw;
  }
  return 'auto';
}

/**
 * Centralises the app-level light/dark/auto preference. Quasar's `Dark` plugin
 * is the single source of truth for applying the class — we just wrap it with
 * persistence and reactive state.
 */
export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(readStoredMode());
  const isDark = ref<boolean>(false);

  function apply(next: ThemeMode): void {
    Dark.set(next === 'auto' ? 'auto' : next === 'dark');
    isDark.value = Dark.isActive;
  }

  function setMode(next: ThemeMode): void {
    mode.value = next;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
    apply(next);
  }

  function toggle(): void {
    setMode(isDark.value ? 'light' : 'dark');
  }

  function init(): void {
    apply(mode.value);
  }

  watch(mode, (next) => apply(next));

  return {
    mode,
    isDark: computed(() => isDark.value),
    setMode,
    toggle,
    init,
  };
});
