"use client";

/**
 * Workspace Switcher
 *
 * Dropdown in the sidebar for switching between personal workspace and org workspaces.
 */

import React, { useState, useRef, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";

export function WorkspaceSwitcher() {
  const { user, orgs, currentOrg, switchOrg, isLoggedIn } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (!isLoggedIn) return null;

  const currentName = currentOrg?.name || "Personal Workspace";
  const currentInitial = currentOrg?.name?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || "P";

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-[#21262d] transition-colors group"
      >
        {/* Avatar */}
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0 shadow-md shadow-indigo-500/20">
          {currentInitial}
        </div>

        {/* Name */}
        <div className="flex-1 text-left min-w-0">
          <p className="text-sm font-medium text-white truncate">{currentName}</p>
          <p className="text-xs text-[#8b95a5] truncate">
            {currentOrg ? currentOrg.role : "Personal"}
          </p>
        </div>

        {/* Chevron */}
        <svg
          className={`w-4 h-4 text-[#8b95a5] transition-transform ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute left-0 right-0 top-full mt-1 bg-[#161b22] border border-[#30363d] rounded-xl shadow-xl shadow-black/40 z-50 overflow-hidden">
          {/* Personal workspace */}
          <button
            onClick={() => { switchOrg(""); setOpen(false); }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 hover:bg-[#21262d] transition-colors ${
              !currentOrg ? "bg-indigo-500/10" : ""
            }`}
          >
            <div className="w-7 h-7 rounded-md bg-[#30363d] flex items-center justify-center text-xs font-bold text-[#c9d1d9]">
              {user?.email?.charAt(0)?.toUpperCase() || "P"}
            </div>
            <div className="flex-1 text-left">
              <p className="text-sm text-white">Personal Workspace</p>
            </div>
            {!currentOrg && <span className="text-xs text-indigo-400">✓</span>}
          </button>

          {orgs.length > 0 && (
            <div className="border-t border-[#21262d] my-1" />
          )}

          {/* Org list */}
          {orgs.map((org) => (
            <button
              key={org.id}
              onClick={() => { switchOrg(org.id); setOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 hover:bg-[#21262d] transition-colors ${
                currentOrg?.id === org.id ? "bg-indigo-500/10" : ""
              }`}
            >
              <div className="w-7 h-7 rounded-md bg-gradient-to-br from-blue-500/30 to-violet-500/30 flex items-center justify-center text-xs font-bold text-white border border-white/10">
                {org.name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 text-left min-w-0">
                <p className="text-sm text-white truncate">{org.name}</p>
                <p className="text-xs text-[#8b95a5]">{org.role}</p>
              </div>
              {currentOrg?.id === org.id && <span className="text-xs text-indigo-400">✓</span>}
            </button>
          ))}

          {/* Create new */}
          <div className="border-t border-[#21262d] mt-1">
            <button className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-[#21262d] transition-colors text-[#8b95a5] hover:text-white">
              <div className="w-7 h-7 rounded-md border border-dashed border-[#484f58] flex items-center justify-center text-xs">
                +
              </div>
              <span className="text-sm">Create Organization</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
