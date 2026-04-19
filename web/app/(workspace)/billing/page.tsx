"use client";

/**
 * Billing Page
 *
 * Current plan, usage meters, upgrade options, and invoice history.
 */

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";

interface PlanInfo {
  id: string;
  name: string;
  tier: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  limits: Record<string, number>;
  features: Record<string, boolean>;
}

interface UsageData {
  period_start: string;
  usage: Record<string, number>;
  limits: Record<string, number>;
}

function UsageMeter({ label, used, limit }: { label: string; used: number; limit: number }) {
  const pct = limit > 0 ? Math.min(used / limit, 1) : 0;
  const isWarning = pct > 0.8;
  const isDanger = pct > 0.95;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-[#c9d1d9]">{label}</span>
        <span className={isDanger ? "text-red-400" : isWarning ? "text-yellow-400" : "text-[#8b95a5]"}>
          {used.toLocaleString()} / {limit.toLocaleString()}
        </span>
      </div>
      <div className="h-2 bg-[#21262d] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isDanger ? "bg-red-500" : isWarning ? "bg-yellow-500" : "bg-gradient-to-r from-indigo-500 to-violet-500"
          }`}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
    </div>
  );
}

function PlanCard({ plan, isCurrentPlan, onUpgrade }: { plan: PlanInfo; isCurrentPlan: boolean; onUpgrade: (planId: string) => void }) {
  const tierColors: Record<string, string> = {
    free: "from-gray-500/20 to-gray-600/20 border-gray-500/30",
    pro: "from-indigo-500/20 to-violet-500/20 border-indigo-500/30",
    team: "from-blue-500/20 to-cyan-500/20 border-blue-500/30",
    school: "from-emerald-500/20 to-green-500/20 border-emerald-500/30",
    enterprise: "from-amber-500/20 to-orange-500/20 border-amber-500/30",
  };

  return (
    <div className={`relative bg-gradient-to-br ${tierColors[plan.tier] || tierColors.free} border rounded-2xl p-6 ${isCurrentPlan ? "ring-2 ring-indigo-500 ring-offset-2 ring-offset-[#0d1117]" : ""}`}>
      {isCurrentPlan && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-indigo-600 rounded-full text-xs font-medium text-white">
          Current Plan
        </div>
      )}
      <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
      <p className="text-sm text-[#8b95a5] mb-4">{plan.description}</p>
      <div className="mb-4">
        {plan.price_monthly > 0 ? (
          <div>
            <span className="text-3xl font-bold text-white">${plan.price_monthly}</span>
            <span className="text-[#8b95a5]">/mo</span>
          </div>
        ) : plan.tier === "enterprise" ? (
          <span className="text-lg font-medium text-white">Custom Pricing</span>
        ) : (
          <span className="text-3xl font-bold text-white">Free</span>
        )}
      </div>
      {!isCurrentPlan && plan.price_monthly > 0 && (
        <button
          onClick={() => onUpgrade(plan.id)}
          className="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-indigo-500/20"
        >
          Upgrade
        </button>
      )}
      {plan.tier === "enterprise" && !isCurrentPlan && (
        <button className="w-full py-2.5 border border-[#30363d] text-white font-semibold rounded-xl hover:bg-[#21262d] transition-colors">
          Contact Sales
        </button>
      )}
    </div>
  );
}

export default function BillingPage() {
  const { planTier } = useAuth();
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [plansRes, usageRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/billing/plans`, { headers: authHeaders() }),
          fetch(`${API_BASE}/api/v1/billing/usage`, { headers: authHeaders() }),
        ]);
        if (plansRes.ok) setPlans(await plansRes.json());
        if (usageRes.ok) setUsage(await usageRes.json());
      } catch {
        // Billing unavailable
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleUpgrade = async (planId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ plan_id: planId }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.checkout_url) {
          window.location.href = data.checkout_url;
        }
      }
    } catch {
      alert("Billing is not configured. Set STRIPE_SECRET_KEY to enable upgrades.");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="animate-pulse text-[#8b95a5]">Loading billing...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0d1117] p-6 md:p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Billing & Plans</h1>
          <p className="text-[#8b95a5]">Manage your subscription and monitor usage</p>
        </div>

        {/* Usage Overview */}
        {usage && (
          <div className="bg-[#161b22]/80 backdrop-blur-xl border border-[#30363d] rounded-2xl p-6">
            <h2 className="text-lg font-semibold text-white mb-6">Current Usage</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <UsageMeter label="Tokens" used={usage.usage.tokens || 0} limit={usage.limits.tokens_per_month || 50000} />
              <UsageMeter label="Messages Today" used={usage.usage.messages || 0} limit={usage.limits.messages_per_day || 30} />
              <UsageMeter label="Uploads" used={usage.usage.uploads || 0} limit={usage.limits.uploads_per_month || 3} />
              <UsageMeter label="Searches Today" used={usage.usage.searches || 0} limit={usage.limits.searches_per_day || 10} />
            </div>
          </div>
        )}

        {/* Plans */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-6">Available Plans</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {plans.map((plan) => (
              <PlanCard key={plan.id} plan={plan} isCurrentPlan={plan.tier === planTier} onUpgrade={handleUpgrade} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
