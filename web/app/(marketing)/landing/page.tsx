"use client";

/**
 * Landing Page
 *
 * Premium marketing page with hero, features, pricing, and CTA.
 * Cinematic dark design with animated gradients and glassmorphism.
 */

import Link from "next/link";
import React, { useEffect, useState } from "react";

const FEATURES = [
  {
    icon: "🧠",
    title: "AI-Powered Tutoring",
    desc: "Conversational AI that adapts to your learning style, explains at your level, and guides you through complex topics.",
  },
  {
    icon: "📚",
    title: "Knowledge Base RAG",
    desc: "Upload textbooks, papers, and docs. Our RAG pipeline indexes them for instant contextual retrieval in every session.",
  },
  {
    icon: "🔬",
    title: "Deep Solve & Reason",
    desc: "Multi-stage reasoning pipeline: plan → reason → write. Solves problems that stump standard chatbots.",
  },
  {
    icon: "🃏",
    title: "Spaced Repetition",
    desc: "AI-generated flashcards with SM-2 scheduling. Never forget what you learn — review at the optimal moment.",
  },
  {
    icon: "📝",
    title: "Quizzes & Exams",
    desc: "Auto-generated quizzes from your material. Exam simulator mode with timers and detailed scoring.",
  },
  {
    icon: "📊",
    title: "Learning Analytics",
    desc: "Track streaks, study time, scores, and progress. Data-driven insights to optimize your learning.",
  },
];

const PLANS = [
  {
    name: "Free", price: "$0", period: "forever", tier: "free",
    features: ["5 sessions/day", "30 messages/day", "1 knowledge base", "Basic flashcards & quizzes", "Community support"],
    cta: "Get Started", highlight: false,
  },
  {
    name: "Pro", price: "$19", period: "/month", tier: "pro",
    features: ["50 sessions/day", "500 messages/day", "10 knowledge bases", "Deep Solve & Research", "Learning paths", "Full analytics", "Adaptive difficulty", "Priority support"],
    cta: "Start Pro Trial", highlight: true,
  },
  {
    name: "Team", price: "$49", period: "/month", tier: "team",
    features: ["Everything in Pro", "Up to 10 seats", "Shared knowledge bases", "Team analytics", "Admin dashboard", "Role management"],
    cta: "Start Team Plan", highlight: false,
  },
];

function FloatingOrb({ className, delay = 0 }: { className: string; delay?: number }) {
  return (
    <div
      className={`absolute rounded-full blur-[100px] opacity-20 animate-pulse ${className}`}
      style={{ animationDelay: `${delay}s`, animationDuration: "4s" }}
    />
  );
}

export default function LandingPage() {
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-[#06060f] text-white overflow-hidden">
      {/* Ambient orbs */}
      <FloatingOrb className="w-[500px] h-[500px] bg-indigo-600 -top-40 -left-40" delay={0} />
      <FloatingOrb className="w-[400px] h-[400px] bg-violet-600 top-1/3 -right-32" delay={1.5} />
      <FloatingOrb className="w-[600px] h-[600px] bg-blue-600 bottom-0 left-1/3" delay={3} />

      {/* Nav */}
      <nav className="relative z-20 flex items-center justify-between px-6 md:px-12 py-5 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-indigo-500/30">
            D
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            DeepTutor
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-sm text-[#8b95a5] hover:text-white transition-colors">
            Sign In
          </Link>
          <Link
            href="/register"
            className="px-4 py-2 text-sm font-medium bg-gradient-to-r from-indigo-600 to-violet-600 rounded-xl hover:from-indigo-500 hover:to-violet-500 transition-all shadow-lg shadow-indigo-500/20"
          >
            Get Started Free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 px-6 md:px-12 pt-20 md:pt-32 pb-20 text-center max-w-5xl mx-auto">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 bg-indigo-500/10 border border-indigo-500/20 rounded-full text-xs font-medium text-indigo-400">
          <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
          AI-Native Learning Platform
        </div>

        <h1
          className="text-5xl md:text-7xl font-extrabold leading-tight mb-6"
          style={{ transform: `translateY(${scrollY * 0.1}px)` }}
        >
          Learn anything,{" "}
          <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
            deeply
          </span>
          .
        </h1>

        <p className="text-lg md:text-xl text-[#8b95a5] max-w-2xl mx-auto mb-10 leading-relaxed">
          DeepTutor is an AI tutor that understands your textbooks, generates personalized quizzes,
          tracks your progress, and adapts to how you learn. Built for serious learners.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/register"
            className="px-8 py-3.5 text-base font-semibold bg-gradient-to-r from-indigo-600 to-violet-600 rounded-2xl hover:from-indigo-500 hover:to-violet-500 transition-all shadow-xl shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:-translate-y-0.5"
          >
            Start Learning Free →
          </Link>
          <Link
            href="#features"
            className="px-8 py-3.5 text-base font-semibold border border-[#30363d] rounded-2xl hover:bg-[#161b22] transition-all text-[#c9d1d9]"
          >
            See Features
          </Link>
        </div>

        {/* Trust badges */}
        <div className="mt-16 flex items-center justify-center gap-8 text-[#484f58] text-xs">
          <span>✦ Open Source</span>
          <span>✦ Self-Hostable</span>
          <span>✦ SOC 2 Ready</span>
          <span>✦ GDPR Compliant</span>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 px-6 md:px-12 py-20 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Everything you need to{" "}
            <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">master any subject</span>
          </h2>
          <p className="text-[#8b95a5] max-w-xl mx-auto">
            Agent-native architecture with multi-stage AI pipelines, not just another chatbot wrapper.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f, i) => (
            <div
              key={i}
              className="group bg-[#0d1117]/60 backdrop-blur-xl border border-[#1c2128] rounded-2xl p-6 hover:border-indigo-500/30 hover:bg-[#161b22]/60 transition-all duration-300 hover:-translate-y-1"
            >
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-indigo-300 transition-colors">{f.title}</h3>
              <p className="text-sm text-[#8b95a5] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="relative z-10 px-6 md:px-12 py-20 max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Simple, transparent{" "}
            <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">pricing</span>
          </h2>
          <p className="text-[#8b95a5]">Start free, upgrade when you need more.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-2xl p-8 border transition-all duration-300 hover:-translate-y-1 ${
                plan.highlight
                  ? "bg-gradient-to-br from-indigo-600/10 to-violet-600/10 border-indigo-500/30 shadow-xl shadow-indigo-500/10"
                  : "bg-[#0d1117]/60 border-[#1c2128] hover:border-[#30363d]"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-indigo-600 to-violet-600 rounded-full text-xs font-bold text-white shadow-lg">
                  Most Popular
                </div>
              )}
              <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
              <div className="mb-6">
                <span className="text-4xl font-extrabold text-white">{plan.price}</span>
                <span className="text-[#8b95a5]">{plan.period}</span>
              </div>
              <ul className="space-y-3 mb-8">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-[#c9d1d9]">
                    <span className="text-indigo-400 mt-0.5">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className={`block text-center py-3 rounded-xl font-semibold transition-all ${
                  plan.highlight
                    ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white hover:from-indigo-500 hover:to-violet-500 shadow-lg shadow-indigo-500/20"
                    : "border border-[#30363d] text-white hover:bg-[#161b22]"
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 px-6 md:px-12 py-20 text-center">
        <div className="max-w-3xl mx-auto bg-gradient-to-br from-indigo-600/10 to-violet-600/10 border border-indigo-500/20 rounded-3xl p-12 backdrop-blur-xl">
          <h2 className="text-3xl font-bold mb-4">Ready to learn deeply?</h2>
          <p className="text-[#8b95a5] mb-8 max-w-lg mx-auto">
            Join thousands of learners using AI to master subjects faster than ever before.
          </p>
          <Link
            href="/register"
            className="inline-block px-8 py-3.5 text-base font-semibold bg-gradient-to-r from-indigo-600 to-violet-600 rounded-2xl hover:from-indigo-500 hover:to-violet-500 transition-all shadow-xl shadow-indigo-500/25"
          >
            Create Free Account
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 px-6 md:px-12 py-8">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-xs">
              D
            </div>
            <span className="text-sm font-semibold text-[#8b95a5]">DeepTutor</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-[#484f58]">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">Support</a>
            <a href="https://github.com/HKUDS/DeepTutor" className="hover:text-white transition-colors">GitHub</a>
          </div>
          <p className="text-xs text-[#484f58]">© 2026 DeepTutor. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
