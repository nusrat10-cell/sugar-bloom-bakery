import { createContext, ReactNode, useContext, useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export interface AuthUser {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: "user" | "admin";
  is_banned?: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, username: string, fullName: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

let accessTokenMemory: string | null = null;

export function getAccessToken(): string | null {
  return accessTokenMemory;
}

function setAccessToken(token: string | null) {
  accessTokenMemory = token;
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs = 4000): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

async function refreshAccessToken(): Promise<string | null> {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/api/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) {
      setAccessToken(null);
      return null;
    }
    const data = await res.json();
    setAccessToken(data.access_token || null);
    return data.access_token || null;
  } catch {
    setAccessToken(null);
    return null;
  }
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (accessTokenMemory) {
    headers.set("Authorization", `Bearer ${accessTokenMemory}`);
  }

  let res = await fetchWithTimeout(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (res.status === 401 && retry && !path.startsWith("/api/auth/")) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetchWithTimeout(`${API_BASE_URL}${path}`, {
        ...options,
        headers,
        credentials: "include",
      });
    }
  }

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const errData = await res.json();
      if (typeof errData?.detail === "string") {
        message = errData.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(message);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCurrentUser = async (): Promise<AuthUser | null> => {
    try {
      return await apiRequest<AuthUser>("/api/auth/me", {}, false);
    } catch {
      const newToken = await refreshAccessToken();
      if (!newToken) return null;
      try {
        return await apiRequest<AuthUser>("/api/auth/me", {}, false);
      } catch {
        return null;
      }
    }
  };

  useEffect(() => {
    let active = true;
    const safetyTimer = window.setTimeout(() => {
      if (active) setLoading(false);
    }, 4500);

    (async () => {
      try {
        const current = await fetchCurrentUser();
        if (active) {
          setUser(current);
        }
      } catch {
        if (active) {
          setUser(null);
        }
      } finally {
        window.clearTimeout(safetyTimer);
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
      window.clearTimeout(safetyTimer);
    };
  }, []);

  const login = async (email: string, password: string) => {
    const data = await apiRequest<{ access_token: string; user: AuthUser }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAccessToken(data.access_token);
    setUser(data.user);
  };

  const signup = async (email: string, username: string, fullName: string, password: string) => {
    const data = await apiRequest<{ access_token: string; user: AuthUser }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, username, full_name: fullName, password }),
    });
    setAccessToken(data.access_token);
    setUser(data.user);
  };

  const logout = async () => {
    try {
      await apiRequest("/api/auth/logout", { method: "POST" }, false);
    } catch {
      // ignore logout error
    }
    setAccessToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    const current = await fetchCurrentUser();
    setUser(current);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}