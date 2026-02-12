import { create } from "zustand";
import api from "@/lib/api";
import { setTokens, clearTokens, isAuthenticated } from "@/lib/auth";

interface AuthState {
  isLoggedIn: boolean;
  isLoading: boolean;
  error: string | null;
  requires2fa: boolean;
  tempToken: string | null;

  login: (username: string, password: string) => Promise<void>;
  verify2fa: (code: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isLoggedIn: isAuthenticated(),
  isLoading: false,
  error: null,
  requires2fa: false,
  tempToken: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null, requires2fa: false, tempToken: null });
    try {
      const { data } = await api.post("/auth/login", { username, password });

      if (data.requires_2fa) {
        set({ isLoading: false, requires2fa: true, tempToken: data.temp_token });
        return;
      }

      setTokens(data.access_token, data.refresh_token);
      set({ isLoggedIn: true, isLoading: false });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { error?: { message?: string } } } };
      const message =
        axiosErr.response?.data?.error?.message || "Login failed. Please try again.";
      set({ isLoading: false, error: message });
    }
  },

  verify2fa: async (code: string) => {
    const { tempToken } = get();
    if (!tempToken) return;

    set({ isLoading: true, error: null });
    try {
      const { data } = await api.post("/auth/2fa/verify", {
        temp_token: tempToken,
        code,
      });
      setTokens(data.access_token, data.refresh_token);
      set({
        isLoggedIn: true,
        isLoading: false,
        requires2fa: false,
        tempToken: null,
      });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { error?: { message?: string } } } };
      const message =
        axiosErr.response?.data?.error?.message || "Invalid 2FA code. Please try again.";
      set({ isLoading: false, error: message });
    }
  },

  logout: () => {
    clearTokens();
    set({
      isLoggedIn: false,
      requires2fa: false,
      tempToken: null,
      error: null,
    });
  },

  clearError: () => set({ error: null }),
}));
