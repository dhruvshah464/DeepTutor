"use client";

/**
 * Admin Dashboard
 *
 * Platform-wide stats, user management, and system health for superadmins.
 */

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";

interface PlatformStats {
  users: { total: number; active: number };
  organizations: { total: number };
  sessions: { total: number };
  subscriptions: { active: number };
  plan_distribution: Record<string, number>;
  uptime_seconds: number;
}

interface AdminUser {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  auth_provider: string;
  email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

function StatTile({ label, value, icon, gradient }: { label: string; value: string | number; icon: string; gradient: string }) {
  return (
    <div className={`rounded-2xl p-5 bg-gradient-to-br ${gradient} border border-white/5`}>
      <div className="flex items-center gap-3 mb-3">
        <span className="text-2xl">{icon}</span>
        <span className="text-sm font-medium text-white/70 uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">{typeof value === "number" ? value.toLocaleString() : value}</p>
    </div>
  );
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default function AdminPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "users" | "audit">("overview");

  useEffect(() => {
    loadStats();
    loadUsers();
  }, []);

  async function loadStats() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/admin/stats`, { headers: authHeaders() });
      if (res.ok) setStats(await res.json());
    } catch {} finally { setLoading(false); }
  }

  async function loadUsers(q = "") {
    try {
      const res = await fetch(`${API_BASE}/api/v1/admin/users?search=${q}&limit=50`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
      }
    } catch {}
  }

  async function toggleUserStatus(userId: string, isActive: boolean) {
    const action = isActive ? "deactivate" : "activate";
    try {
      await fetch(`${API_BASE}/api/v1/admin/users/${userId}/${action}`, {
        method: "POST",
        headers: authHeaders(),
      });
      loadUsers(search);
    } catch {}
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadUsers(search);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="animate-pulse text-[#8b95a5]">Loading admin panel...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0d1117] p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">Admin Panel</h1>
            <p className="text-[#8b95a5]">Platform management and monitoring</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/10 border border-red-500/20 rounded-full">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            <span className="text-xs font-medium text-red-400">Superadmin</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-[#161b22] rounded-xl p-1 w-fit">
          {(["overview", "users", "audit"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                  : "text-[#8b95a5] hover:text-white hover:bg-[#21262d]"
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatTile label="Total Users" value={stats.users.total} icon="👥" gradient="from-blue-600/20 to-blue-800/20" />
              <StatTile label="Active Users" value={stats.users.active} icon="✅" gradient="from-emerald-600/20 to-emerald-800/20" />
              <StatTile label="Organizations" value={stats.organizations.total} icon="🏢" gradient="from-violet-600/20 to-violet-800/20" />
              <StatTile label="Chat Sessions" value={stats.sessions.total} icon="💬" gradient="from-amber-600/20 to-amber-800/20" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Plan Distribution */}
              <div className="bg-[#161b22]/80 border border-[#30363d] rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-[#c9d1d9] mb-4 uppercase tracking-wider">Plan Distribution</h3>
                <div className="space-y-3">
                  {Object.entries(stats.plan_distribution).map(([tier, count]) => (
                    <div key={tier} className="flex items-center justify-between">
                      <span className="text-sm text-[#c9d1d9] capitalize">{tier}</span>
                      <span className="text-sm font-bold text-white">{count}</span>
                    </div>
                  ))}
                  {Object.keys(stats.plan_distribution).length === 0 && (
                    <p className="text-sm text-[#484f58]">No active subscriptions yet</p>
                  )}
                </div>
              </div>

              {/* System Health */}
              <div className="bg-[#161b22]/80 border border-[#30363d] rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-[#c9d1d9] mb-4 uppercase tracking-wider">System</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-[#8b95a5]">Uptime</span>
                    <span className="text-sm font-medium text-white">{formatUptime(stats.uptime_seconds)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-[#8b95a5]">Active Subscriptions</span>
                    <span className="text-sm font-medium text-white">{stats.subscriptions.active}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === "users" && (
          <div className="space-y-4">
            <form onSubmit={handleSearch} className="flex gap-3">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search users by email..."
                className="flex-1 px-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white placeholder-[#484f58] focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
              <button type="submit" className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 transition-colors font-medium">
                Search
              </button>
            </form>

            <div className="bg-[#161b22]/80 border border-[#30363d] rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#30363d]">
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8b95a5] uppercase">Email</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8b95a5] uppercase">Role</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8b95a5] uppercase">Provider</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8b95a5] uppercase">Status</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8b95a5] uppercase">Joined</th>
                    <th className="text-right px-5 py-3 text-xs font-semibold text-[#8b95a5] uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-[#21262d] hover:bg-[#161b22] transition-colors">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-white">{u.email}</span>
                          {u.email_verified && <span className="text-xs text-emerald-400">✓</span>}
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          u.role === "superadmin" ? "bg-red-500/10 text-red-400" : "bg-[#21262d] text-[#8b95a5]"
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-sm text-[#8b95a5]">{u.auth_provider}</td>
                      <td className="px-5 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          u.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                        }`}>
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-sm text-[#8b95a5]">{u.created_at?.split("T")[0]}</td>
                      <td className="px-5 py-3 text-right">
                        {u.role !== "superadmin" && (
                          <button
                            onClick={() => toggleUserStatus(u.id, u.is_active)}
                            className={`text-xs px-3 py-1 rounded-lg transition-colors ${
                              u.is_active
                                ? "text-red-400 hover:bg-red-500/10"
                                : "text-emerald-400 hover:bg-emerald-500/10"
                            }`}
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {users.length === 0 && (
                <p className="text-sm text-[#484f58] text-center py-8">No users found</p>
              )}
            </div>
          </div>
        )}

        {/* Audit Tab */}
        {activeTab === "audit" && (
          <div className="bg-[#161b22]/80 border border-[#30363d] rounded-2xl p-6">
            <h3 className="text-sm font-semibold text-[#c9d1d9] mb-4 uppercase tracking-wider">Audit Log</h3>
            <p className="text-sm text-[#484f58]">Audit log entries will appear here as users perform actions on the platform.</p>
          </div>
        )}
      </div>
    </div>
  );
}
