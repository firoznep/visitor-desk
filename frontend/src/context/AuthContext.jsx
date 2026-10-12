import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, setCsrfToken } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);     // { username, full_name, role, must_change_password }
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // A page refresh loses the in-memory CSRF token but keeps the HttpOnly session cookie.
    // There's no way to recover the CSRF token without a fresh login in this version, so a
    // refreshed page always needs to sign in again — a deliberate, simple tradeoff.
    setLoading(false);
  }, []);

  const login = useCallback(async (username, password) => {
    const me = await api.login(username, password);
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setCsrfToken(null);
      setUser(null);
    }
  }, []);

  const markPasswordChanged = useCallback(() => {
    setUser((u) => (u ? { ...u, must_change_password: false } : u));
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, markPasswordChanged }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
