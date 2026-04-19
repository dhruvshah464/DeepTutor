"use client";

/**
 * Auth Context Provider
 *
 * Global authentication state with user profile, org switching, and plan info.
 */

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  type MeResponse,
  type OrgInfo,
  type UserProfile,
  clearTokens,
  getMe,
  isAuthenticated,
  login as authLogin,
  logout as authLogout,
  register as authRegister,
} from "@/lib/auth";

interface AuthState {
  isLoading: boolean;
  isLoggedIn: boolean;
  user: UserProfile | null;
  orgs: OrgInfo[];
  currentOrg: OrgInfo | null;
  planTier: string;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  switchOrg: (orgId: string) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isLoading: true,
    isLoggedIn: false,
    user: null,
    orgs: [],
    currentOrg: null,
    planTier: "free",
  });

  const refresh = useCallback(async () => {
    if (!isAuthenticated()) {
      setState((s) => ({ ...s, isLoading: false, isLoggedIn: false }));
      return;
    }
    try {
      const me: MeResponse = await getMe();
      setState({
        isLoading: false,
        isLoggedIn: true,
        user: me.user,
        orgs: me.orgs,
        currentOrg: me.current_org || null,
        planTier: me.plan_tier,
      });
    } catch {
      clearTokens();
      setState({
        isLoading: false,
        isLoggedIn: false,
        user: null,
        orgs: [],
        currentOrg: null,
        planTier: "free",
      });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      await authLogin(email, password);
      await refresh();
    },
    [refresh]
  );

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      await authRegister(email, password, displayName);
      await refresh();
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    await authLogout();
    setState({
      isLoading: false,
      isLoggedIn: false,
      user: null,
      orgs: [],
      currentOrg: null,
      planTier: "free",
    });
  }, []);

  const switchOrg = useCallback(
    (orgId: string) => {
      const org = state.orgs.find((o) => o.id === orgId) || null;
      setState((s) => ({ ...s, currentOrg: org }));
    },
    [state.orgs]
  );

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, refresh, switchOrg }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
