"use client";

/**
 * Team Management Page
 *
 * Org member list, invite flow, and role management.
 */

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";

interface Member {
  user_id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  joined_at: string;
}

const ROLE_OPTIONS = ["learner", "educator", "analyst", "admin", "owner"];
const ROLE_COLORS: Record<string, string> = {
  owner: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  admin: "bg-red-500/10 text-red-400 border-red-500/20",
  educator: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  learner: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  analyst: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  support: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

export default function TeamPage() {
  const { currentOrg } = useAuth();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("learner");
  const [inviteStatus, setInviteStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  useEffect(() => {
    if (currentOrg) loadMembers();
    else setLoading(false);
  }, [currentOrg]);

  async function loadMembers() {
    if (!currentOrg) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/orgs/${currentOrg.id}/members`, { headers: authHeaders() });
      if (res.ok) setMembers(await res.json());
    } catch {} finally { setLoading(false); }
  }

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!currentOrg || !inviteEmail) return;
    setInviteStatus("sending");
    try {
      const res = await fetch(`${API_BASE}/api/v1/orgs/${currentOrg.id}/members/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      if (res.ok) {
        setInviteStatus("sent");
        setInviteEmail("");
        setTimeout(() => setInviteStatus("idle"), 3000);
      } else {
        setInviteStatus("error");
      }
    } catch {
      setInviteStatus("error");
    }
  }

  if (!currentOrg) {
    return (
      <div className="min-h-screen bg-[#0d1117] p-6 md:p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-4">Team</h1>
          <div className="bg-[#161b22]/80 border border-[#30363d] rounded-2xl p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-indigo-500/10 flex items-center justify-center">
              <span className="text-3xl">🏢</span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No Organization</h3>
            <p className="text-[#8b95a5] mb-4">Create or join an organization to manage team members.</p>
            <button className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-xl font-medium hover:from-indigo-500 hover:to-violet-500 transition-all shadow-lg shadow-indigo-500/20">
              Create Organization
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0d1117] p-6 md:p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Team — {currentOrg.name}</h1>
          <p className="text-[#8b95a5]">{members.length} member{members.length !== 1 ? "s" : ""}</p>
        </div>

        {/* Invite */}
        <div className="bg-[#161b22]/80 border border-[#30363d] rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-[#c9d1d9] mb-4 uppercase tracking-wider">Invite Member</h3>
          <form onSubmit={handleInvite} className="flex flex-col sm:flex-row gap-3">
            <input
              type="email"
              required
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="colleague@example.com"
              className="flex-1 px-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white placeholder-[#484f58] focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="px-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={inviteStatus === "sending"}
              className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 transition-colors font-medium disabled:opacity-50"
            >
              {inviteStatus === "sending" ? "Sending..." : inviteStatus === "sent" ? "✓ Sent!" : "Invite"}
            </button>
          </form>
          {inviteStatus === "error" && (
            <p className="mt-2 text-sm text-red-400">Failed to send invitation. User may already be a member.</p>
          )}
        </div>

        {/* Member List */}
        <div className="bg-[#161b22]/80 border border-[#30363d] rounded-2xl overflow-hidden">
          <div className="px-6 py-4 border-b border-[#30363d]">
            <h3 className="text-sm font-semibold text-[#c9d1d9] uppercase tracking-wider">Members</h3>
          </div>
          {loading ? (
            <p className="text-sm text-[#484f58] text-center py-8">Loading...</p>
          ) : (
            <div className="divide-y divide-[#21262d]">
              {members.map((m) => (
                <div key={m.user_id} className="flex items-center justify-between px-6 py-4 hover:bg-[#161b22] transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center text-white font-bold text-sm">
                      {(m.display_name || m.email).charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{m.display_name || m.email}</p>
                      <p className="text-xs text-[#8b95a5]">{m.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2.5 py-1 rounded-full border ${ROLE_COLORS[m.role] || ROLE_COLORS.learner}`}>
                      {m.role}
                    </span>
                    <span className="text-xs text-[#484f58]">
                      Joined {m.joined_at?.split("T")[0]}
                    </span>
                  </div>
                </div>
              ))}
              {members.length === 0 && (
                <p className="text-sm text-[#484f58] text-center py-8">No members yet. Invite your first team member!</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
