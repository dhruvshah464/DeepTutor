/**
 * Auth API Client
 *
 * Client-side authentication utilities: JWT storage, refresh, headers.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";

const TOKEN_KEY = "dt_access_token";
const REFRESH_KEY = "dt_refresh_token";

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  email_verified: boolean;
  role: string;
  is_active: boolean;
  auth_provider: string;
  display_name?: string;
  avatar_url?: string;
  bio?: string;
  timezone?: string;
  language?: string;
  education_level?: string;
  learning_goals?: Record<string, unknown>;
  subjects_of_interest?: string[];
  theme?: string;
  explanation_level?: string;
  created_at?: string;
}

export interface OrgInfo {
  id: string;
  name: string;
  slug: string;
  description?: string;
  logo_url?: string;
  role: string;
  member_count?: number;
  plan_tier?: string;
}

export interface MeResponse {
  user: UserProfile;
  orgs: OrgInfo[];
  current_org?: OrgInfo;
  plan_tier: string;
}

// ── Token Storage ──

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

// Presence-only cookie (no token value) so the Next.js middleware route
// guard can redirect logged-out visitors away from SaaS pages before the
// page renders. Middleware runs at the edge and cannot read localStorage,
// which is where the real bearer tokens live and stay — this cookie never
// carries the token itself, only a boolean "a session exists" flag.
const SESSION_COOKIE = "dt_session";

function setSessionCookie(): void {
  document.cookie = `${SESSION_COOKIE}=1; path=/; max-age=2592000; SameSite=Lax`;
}

function clearSessionCookie(): void {
  document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

export function setTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  setSessionCookie();
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  clearSessionCookie();
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

// ── Auth Headers ──

export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

// ── API Calls ──

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });

  // Auto-refresh on 401
  if (res.status === 401 && getRefreshToken()) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
          ...(options.headers || {}),
        },
      });
    }
  }

  return res;
}

export async function register(
  email: string,
  password: string,
  displayName?: string
): Promise<AuthTokens> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Registration failed" }));
    throw new Error(err.detail || "Registration failed");
  }
  const tokens: AuthTokens = await res.json();
  setTokens(tokens);
  return tokens;
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Login failed");
  }
  const tokens: AuthTokens = await res.json();
  setTokens(tokens);
  return tokens;
}

export async function requestMagicLink(email: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/auth/magic-link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function verifyMagicLink(token: string): Promise<AuthTokens> {
  const res = await fetch(`${API_BASE}/api/v1/auth/magic-link/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) throw new Error("Invalid or expired magic link");
  const tokens: AuthTokens = await res.json();
  setTokens(tokens);
  return tokens;
}

export async function refreshTokens(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    const tokens: AuthTokens = await res.json();
    setTokens(tokens);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export async function logout(): Promise<void> {
  try {
    await authFetch("/api/v1/auth/logout", { method: "POST" });
  } finally {
    clearTokens();
  }
}

export async function getMe(): Promise<MeResponse> {
  const res = await authFetch("/api/v1/auth/me");
  if (!res.ok) throw new Error("Failed to fetch profile");
  return res.json();
}

// ── WebSocket Auth ──

export function getAuthenticatedWsUrl(basePath: string): string {
  const token = getAccessToken();
  const wsBase = API_BASE.replace(/^http/, "ws");
  return token ? `${wsBase}${basePath}?token=${token}` : `${wsBase}${basePath}`;
}
