"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getToken, clearToken, getMe } from "./api";

interface User {
  display_name: string;
  picture_url: string;
  is_admin?: boolean;
}

interface AuthState {
  loading: boolean;
  authenticated: boolean;
  user: User | null;
  logout: () => void;
  refresh: () => void;
}

const AuthContext = createContext<AuthState>({
  loading: true,
  authenticated: false,
  user: null,
  logout: () => {},
  refresh: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  const checkAuth = useCallback(() => {
    const token = getToken();
    if (!token) {
      setAuthenticated(false);
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    getMe()
      .then((res) => {
        if (res.authenticated && res.user) {
          setAuthenticated(true);
          setUser(res.user);
        } else {
          clearToken();
          setAuthenticated(false);
          setUser(null);
        }
      })
      .catch(() => {
        clearToken();
        setAuthenticated(false);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Listen for token changes from other tabs or /auth/success
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === "nk_token") checkAuth();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [checkAuth]);

  const logout = useCallback(() => {
    clearToken();
    setAuthenticated(false);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ loading, authenticated, user, logout, refresh: checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
