"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getToken, clearToken, getMe } from "./api";

interface User {
  display_name: string;
  picture_url: string;
}

interface AuthState {
  loading: boolean;
  authenticated: boolean;
  user: User | null;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  loading: true,
  authenticated: false,
  user: null,
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then((res) => {
        if (res.authenticated && res.user) {
          setAuthenticated(true);
          setUser(res.user);
        } else {
          clearToken();
        }
      })
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setAuthenticated(false);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ loading, authenticated, user, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
