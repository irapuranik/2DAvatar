import { create } from "zustand";

type ThemeMode = "light" | "dark";

interface ThemeState {
  mode: ThemeMode;
  toggle: () => void;
}

const stored = localStorage.getItem("aimms-theme-mode") as ThemeMode | null;
const initial: ThemeMode = stored === "dark" ? "dark" : "light";

export const useThemeStore = create<ThemeState>((set) => ({
  mode: initial,
  toggle: () =>
    set((state) => {
      const next = state.mode === "light" ? "dark" : "light";
      localStorage.setItem("aimms-theme-mode", next);
      document.documentElement.className = next;
      return { mode: next };
    }),
}));
