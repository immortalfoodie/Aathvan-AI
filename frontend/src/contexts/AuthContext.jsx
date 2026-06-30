/**
 * Auth context — stores JWT in-memory and provides login/signup/logout.
 *
 * ⚠️ PLACEHOLDER SECURITY: The token lives in React state (memory).
 * This is deliberately NOT localStorage — it's safer against XSS but means
 * the user loses their session on page refresh. For production, switch to
 * httpOnly cookie-based auth with a refresh token endpoint.
 */
import { createContext, useContext, useState, useCallback, useEffect } from "react";
import client, { setAccessToken, clearAccessToken, getAccessToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Try to fetch user info if a token exists in memory (e.g. after HMR)
  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      client
        .get("/auth/me")
        .then((res) => setUser(res.data))
        .catch(() => {
          clearAccessToken();
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const signup = useCallback(async (email, password, name) => {
    const res = await client.post("/auth/signup", { email, password, name });
    setAccessToken(res.data.access_token);
    const me = await client.get("/auth/me");
    setUser(me.data);
    return me.data;
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await client.post("/auth/login", { email, password });
    setAccessToken(res.data.access_token);
    const me = await client.get("/auth/me");
    setUser(me.data);
    return me.data;
  }, []);

  const loginWithToken = useCallback(async (token) => {
    setAccessToken(token);
    const me = await client.get("/auth/me");
    setUser(me.data);
    return me.data;
  }, []);

  const logout = useCallback(() => {
    clearAccessToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signup, login, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
