"use client";

/**
 * Learner Dashboard
 *
 * Premium dashboard with progress rings, streak tracking, and activity overview.
 */

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";

interface AnalyticsData {
  period_days: number;
  sessions: { total: number; messages: number };
  learning: {
    total_study_time_seconds: number;
    average_score: number | null;
    activity_by_type: Record<string, number>;
    streak_days: number;
    active_days: number;
  };
  quizzes: { total_attempts: number; average_score: number };
  paths: { active: number };
  flashcards: { total_decks: number };
}

function ProgressRing({ value, max, size = 80, label, color }: { value: number; max: number; size?: number; label: string; color: string }) {
  const pct = max > 0 ? Math.min(value / max, 1) : 0;
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
          <circle
            cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="6"
            strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold text-white">{Math.round(pct * 100)}%</span>
        </div>
      </div>
      <span className="text-xs text-[#8b95a5] font-medium">{label}</span>
    </div>
  );
}

function StatCard({ icon, label, value, subtext, gradient }: { icon: string; label: string; value: string | number; subtext?: string; gradient: string }) {
  return (
    <div className="bg-[#161b22]/80 backdrop-blur-xl border border-[#30363d] rounded-2xl p-5 hover:border-[#484f58] transition-all duration-300 group">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-lg shadow-lg`}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold text-white mb-1 group-hover:text-indigo-200 transition-colors">{value}</p>
      <p className="text-sm text-[#8b95a5]">{label}</p>
      {subtext && <p className="text-xs text-[#484f58] mt-1">{subtext}</p>}
    </div>
  );
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export default function DashboardPage() {
  const { user, planTier, isLoggedIn, isLoading } = useAuth();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/analytics/learner?days=30`, {
          headers: authHeaders(),
        });
        if (res.ok) {
          setAnalytics(await res.json());
        }
      } catch {
        // Analytics unavailable
      } finally {
        setLoading(false);
      }
    }
    if (isLoggedIn) load();
    else setLoading(false);
  }, [isLoggedIn]);

  if (isLoading || loading) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="animate-pulse text-[#8b95a5]">Loading dashboard...</div>
      </div>
    );
  }

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 18) return "Good afternoon";
    return "Good evening";
  })();

  const displayName = user?.display_name || user?.email?.split("@")[0] || "Learner";

  return (
    <div className="min-h-screen bg-[#0d1117] p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">
              {greeting}, <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">{displayName}</span>
            </h1>
            <p className="text-[#8b95a5]">
              Here&apos;s your learning overview for the past 30 days
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-gradient-to-r from-indigo-500/10 to-violet-500/10 border border-indigo-500/20 rounded-full text-xs font-medium text-indigo-400 uppercase tracking-wider">
              {planTier} plan
            </span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon="🔥"
            label="Day Streak"
            value={analytics?.learning.streak_days || 0}
            subtext={`${analytics?.learning.active_days || 0} active days`}
            gradient="from-orange-500/80 to-red-500/80"
          />
          <StatCard
            icon="💬"
            label="Sessions"
            value={analytics?.sessions.total || 0}
            subtext={`${analytics?.sessions.messages || 0} messages`}
            gradient="from-blue-500/80 to-cyan-500/80"
          />
          <StatCard
            icon="⏱️"
            label="Study Time"
            value={formatTime(analytics?.learning.total_study_time_seconds || 0)}
            subtext="Total learning time"
            gradient="from-emerald-500/80 to-green-500/80"
          />
          <StatCard
            icon="🎯"
            label="Avg Score"
            value={analytics?.learning.average_score ? `${Math.round(analytics.learning.average_score)}%` : "—"}
            subtext="Quiz & flashcard avg"
            gradient="from-violet-500/80 to-purple-500/80"
          />
        </div>

        {/* Progress & Activity */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Progress Rings */}
          <div className="bg-[#161b22]/80 backdrop-blur-xl border border-[#30363d] rounded-2xl p-6">
            <h3 className="text-sm font-semibold text-[#c9d1d9] mb-6 uppercase tracking-wider">Progress</h3>
            <div className="flex justify-around">
              <ProgressRing value={analytics?.quizzes.average_score || 0} max={100} label="Quizzes" color="#818cf8" />
              <ProgressRing value={analytics?.learning.active_days || 0} max={30} label="Active Days" color="#34d399" />
              <ProgressRing value={analytics?.learning.streak_days || 0} max={30} label="Streak" color="#fb923c" />
            </div>
          </div>

          {/* Activity Breakdown */}
          <div className="bg-[#161b22]/80 backdrop-blur-xl border border-[#30363d] rounded-2xl p-6">
            <h3 className="text-sm font-semibold text-[#c9d1d9] mb-6 uppercase tracking-wider">Activity Types</h3>
            <div className="space-y-4">
              {Object.entries(analytics?.learning.activity_by_type || {}).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm text-[#c9d1d9] capitalize">{type}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-24 h-2 bg-[#21262d] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, (count / Math.max(1, Object.values(analytics?.learning.activity_by_type || {}).reduce((a, b) => a + b, 0))) * 100)}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-white w-8 text-right">{count}</span>
                  </div>
                </div>
              ))}
              {Object.keys(analytics?.learning.activity_by_type || {}).length === 0 && (
                <p className="text-sm text-[#484f58] text-center py-4">No activity yet. Start learning!</p>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-[#161b22]/80 backdrop-blur-xl border border-[#30363d] rounded-2xl p-6">
            <h3 className="text-sm font-semibold text-[#c9d1d9] mb-6 uppercase tracking-wider">Quick Actions</h3>
            <div className="space-y-3">
              {[
                { label: "Start a Chat", href: "/", icon: "💬", desc: "Ask anything to your AI tutor" },
                { label: "Review Flashcards", href: "#", icon: "🃏", desc: "Cards due for review" },
                { label: "Take a Quiz", href: "#", icon: "📝", desc: "Test your knowledge" },
                { label: "Create Learning Path", href: "#", icon: "🗺️", desc: "Plan your studies" },
              ].map((action) => (
                <a
                  key={action.label}
                  href={action.href}
                  className="flex items-center gap-3 p-3 rounded-xl hover:bg-[#21262d] transition-colors group"
                >
                  <span className="text-xl">{action.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-white group-hover:text-indigo-300 transition-colors">{action.label}</p>
                    <p className="text-xs text-[#484f58]">{action.desc}</p>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
