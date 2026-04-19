"use client";

/**
 * User Menu
 *
 * Avatar dropdown with navigation links, plan badge, and logout.
 */

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

export function UserMenu() {
  const { user, planTier, isLoggedIn, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (!isLoggedIn) {
    return (
      <div className="flex items-center gap-2">
        <Link href="/login" className="px-3 py-1.5 text-sm text-[#8b95a5] hover:text-white transition-colors">
          Sign In
        </Link>
        <Link
          href="/register"
          className="px-3 py-1.5 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors"
        >
          Sign Up
        </Link>
      </div>
    );
  }

  const initial = (user?.display_name || user?.email || "U").charAt(0).toUpperCase();
  const tierColors: Record<string, string> = {
    free: "bg-gray-500/10 text-gray-400",
    pro: "bg-indigo-500/10 text-indigo-400",
    team: "bg-blue-500/10 text-blue-400",
    school: "bg-emerald-500/10 text-emerald-400",
    enterprise: "bg-amber-500/10 text-amber-400",
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-sm hover:ring-2 hover:ring-indigo-400/50 transition-all"
      >
        {initial}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-[#161b22] border border-[#30363d] rounded-xl shadow-xl shadow-black/40 z-50 overflow-hidden">
          {/* User info */}
          <div className="px-4 py-3 border-b border-[#21262d]">
            <p className="text-sm font-medium text-white truncate">{user?.display_name || user?.email}</p>
            <p className="text-xs text-[#8b95a5] truncate">{user?.email}</p>
            <span className={`inline-block mt-1.5 text-xs px-2 py-0.5 rounded-full uppercase tracking-wider ${tierColors[planTier] || tierColors.free}`}>
              {planTier}
            </span>
          </div>

          {/* Links */}
          <div className="py-1">
            {[
              { href: "/dashboard", label: "Dashboard", icon: "📊" },
              { href: "/billing", label: "Billing", icon: "💳" },
              { href: "/team", label: "Team", icon: "👥" },
              ...(user?.role === "superadmin" ? [{ href: "/admin", label: "Admin Panel", icon: "⚙️" }] : []),
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-4 py-2 text-sm text-[#c9d1d9] hover:bg-[#21262d] hover:text-white transition-colors"
              >
                <span>{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>

          {/* Logout */}
          <div className="border-t border-[#21262d] py-1">
            <button
              onClick={() => { logout(); setOpen(false); }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <span>🚪</span>
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
