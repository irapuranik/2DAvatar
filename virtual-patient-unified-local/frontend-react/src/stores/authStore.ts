import { create } from "zustand";
import { apiFetch, BACKEND_URL } from "../api/client";
import { getStoredToken, setStoredToken } from "../lib/tokenStorage";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "student";
  is_active: boolean;
  created_at: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, displayName: string) => Promise<"logged_in" | "confirmation_needed">;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
}

async function postAuth(path: string, body: object): Promise<{ access_token: string }> {
  const base = BACKEND_URL || "";
  const res = await fetch(`${base}/api/auth${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Request failed");
  }
  return res.json();
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isLoading: true,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const { access_token } = await postAuth("/login", { email, password });
      const appUser = await apiFetch<User>("/auth/me", { token: access_token });
      setStoredToken(access_token);
      set({ token: access_token, user: appUser, isLoading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  signup: async (email, password, displayName) => {
    set({ isLoading: true, error: null });
    try {
      const { access_token } = await postAuth("/register", {
        email,
        password,
        display_name: displayName,
      });
      const appUser = await apiFetch<User>("/auth/me", { token: access_token });
      setStoredToken(access_token);
      set({ token: access_token, user: appUser, isLoading: false, error: null });
      return "logged_in";
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Signup failed";
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  logout: async () => {
    setStoredToken(null);
    set({ token: null, user: null });
  },

  restoreSession: async () => {
    set({ isLoading: true });
    try {
      const accessToken = getStoredToken();
      if (!accessToken) {
        set({ token: null, user: null, isLoading: false });
        return;
      }
      const appUser = await apiFetch<User>("/auth/me", { token: accessToken });
      set({ token: accessToken, user: appUser, isLoading: false });
    } catch {
      setStoredToken(null);
      set({ token: null, user: null, isLoading: false });
    }
  },
}));
