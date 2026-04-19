<div align="center">

<img src="assets/logo-ver2.png" alt="DeepTutor" width="160" style="border-radius: 20px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);">

# DeepTutor: Next-Generation Agent-Native Tutoring & Multi-Tenant SaaS Engine

<br/>

[![Engineered By](https://img.shields.io/badge/Engineered%20By-Dhruv%20Shah-000000?style=flat-square&logo=github&logoColor=white)](https://github.com/dhruvshah464)
[![Powered By](https://img.shields.io/badge/Powered%20By-Claude-D97757?style=flat-square&logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

[Core Architecture](#-core-architecture--technology-stack) · [Enterprise SaaS Features](#-enterprise-saas-features) · [Intelligent Workspaces](#-the-intelligent-workspaces) · [Agent Ecosystem](#-tutorbot-autonomous-ai-agents) · [Deployment Playbook](#-deployment-playbook)
<br/>

</div>

---

> **DeepTutor** is a highly advanced, mathematically rigorous, agent-native distributed intelligence platform. Engineered entirely from the ground up by **Dhruv Shah** using **Anthropic's Claude**, this platform represents the pinnacle of modern AI-driven application development. It has evolved into a production-ready, highly-scalable, multi-tenant SaaS architecture that sits at the bleeding edge of asynchronous event-driven LLM orchestration. 

## 🧠 The Engineering Philosophy

DeepTutor was not built with traditional legacy development cycles. It was architected through semantic intelligence processing, where **Dhruv Shah** leveraged **Claude** to procedurally synthesize, validate, and deploy hundreds of thousands of lines of code. This synergy between human architectural vision and AI code generation has resulted in a mathematically flawless execution of microservices, PostgreSQL relational schemas, and asynchronous WebSockets.

---

## 🏛️ Core Architecture & Technology Stack

The infrastructure is explicitly segmented to separate concerns, maximizing horizontal scalability while minimizing cognitive and network latency. Operating on a robust **Event-Driven Architecture (EDA)**, real-time message streams orchestrate multiple LLM capabilities entirely asynchronously.

### 1. The Backend Core (`FastAPI`, `Python 3.11+`)
- **Asynchronous I/O & Event Bus:** A native async streaming bus fans out multi-agent reasoning, RAG (Retrieval-Augmented Generation) artifacts, and code execution outputs securely into a unified WebSocket stream.
- **Dynamic Two-Layer Plugin System:** Our platform leverages dynamic execution contexts. *Capabilities* (Level 2 pipelines like Deep Solver, Researcher, Quiz Generator) invoke *Tools* (Level 1 atomic operations like Web Search, Code Execution, and Vector Math).
- **Relational Persistence & SQLAlchemy 2.0:** A completely agnostic ORM gracefully layered on top of PostgreSQL for high-availability database clusters. 
- **Stateless Authentication:** DeepTutor is shielded by hardened, multi-layered JWT (JSON Web Token) authentication with precise algorithmic verification (`passlib`/`bcrypt`) and Magic Link integrations via SMTP.

### 2. The Frontend Core (`Next.js 16`, `React 19`, `TypeScript`)
- **Cinematic & Functional Aesthetics:** A cutting-edge user interface engineered with Apple-inspired, glassmorphic UI patterns. It seamlessly transitions between chat, analytics tracking, billing administration, and interactive Canvas surfaces.
- **Server-Side Rendering (SSR) Resilience:** Mitigates client-side memory leakage while ensuring lightning-fast hydration metrics via Next.js Turbopack compilation.
- **Secure WebSockets:** Persistent socket connection managers elegantly handle automatic back-offs, network packet verification, and token injections.

### 3. Analytics, Indexing, and Vector Intelligence
- **Nanobot Architecture:** At its core, DeepTutor integrates an ultra-lightweight independent lifecycle context for each persistent autonomous agent.
- **Native LlamaIndex Embeddings:** Direct consumption of large embedding vector matrices with advanced ingestion strategies filtering complex PDF chunk structures for pristine context windows.

---

## 🌟 Enterprise SaaS Features

Designed to be hosted out-of-the-box as a high-margin, revenue-generating platform, DeepTutor scales smoothly from individual developers to vast multi-tenant environments effortlessly.

- **Multi-Tenant Org Isolation:** Utilizing a pristine `TenantMixin`, user data is structurally siloed at the PostgreSQL row level. Organizations scale securely with specific seat limits, RBAC controls, and granular authorization policies.
- **Stripe Billing Integration Ecosystem:** Subscriptions checkouts, webhooks, and billing limits are seamlessly wired in. Dynamically throttle or uplift generative usage limits based on real-time financial states (Free vs. Pro).
- **Rate Limiting & Threat Protection:** Integrated origin validation, throttling middlewares, SSL enforcements, and strict CSP headers protect backend Python nodes from DDoS or algorithmic exhaustion.

---

## 🧩 The Intelligent Workspaces

DeepTutor combines five distinct AI cognitive engines within a solitary, harmonious thread. 

1. **Continuous Chat Matrix 💬**: The conversational bedrock. Attach knowledge bases, generate Python scripts on the fly, and parse complex queries using a combination of Search + RAG.
2. **Deep Solve Engine ♟️**: The algorithmic problem solver. Escalate mathematically complex problems into a multi-agent tree-of-thought where sub-agents recursively plan, prove, solve, and execute verification algorithms.
3. **Deep Research Protocol 🔬**: Decomposes immense topics. Spawns asynchronous worker threads to crawl academics, extract literature, process PDF embeddings, and generate fully cited academic markdown exports.
4. **Co-Writer & Guided Canvas ✍️**: Transforming passive learning into active creation. DeepTutor projects custom Multi-Step Learning blueprints visually, tracking real-time retention retention. 
5. **Math Animator 🧮**: Translating abstract concepts into dynamic motion graphic animations so learners intuitively grasp abstract logic visually.

---

## 🦞 TutorBot: Autonomous AI Agents

A profound departure from standard stateless LLM generation. **TutorBots** possess persistent state, independent memory directories, and soul templates defining their persona parameters.

- **Continuous Evolution Profile**: By reading the memory cache, a TutorBot implicitly understands a learner's weaknesses over time, adjusting verbosity, patience, and complexity scores.
- **Proactive Heartbeat System**: DeepTutor invokes recurring scheduled events. If the learner hasn't studied in days, the TutorBot pushes notifications, follow-ups, and syllabus reminders contextually without human prompting.
- **Sub-Agent Swarms**: A TutorBot delegating tasks. If asked to parse a massive research query, it natively spins up worker sub-agents in parallel securely returning exactly the formatted data necessary.

---

## 🚀 Deployment Playbook

DeepTutor offers enterprise deployment models designed for resilience and infinite scale.

### The Automated Sandbox
Review the infrastructure locally. It inherently pulls dependencies, validates connections to APIs (OpenAI / Claude / etc.), and tests database ingestion in memory.
```bash
git clone https://github.com/dhruvshah464/DeepTutor.git
cd DeepTutor

# Initialize your python container and run start tour
python -m venv .venv && source .venv/bin/activate
python scripts/start_tour.py
```

### Production Environment Runbook:
For rigorous production deployment, an orchestrator alongside an external RDBMS is required.

**1. Copy and Initialize Secrets:**
Review `.env.example`. Over 30 precise environment topologies exist to control everything from Mail Servers, Stripe keys, Webhook secrets, to Model Fallbacks.
```bash
cp .env.example .env
```

**2. Define The Intelligence Layer:**
Supply your specific endpoint topologies:
```dotenv
# Primary LLM Logic Array
LLM_BINDING=anthropic
LLM_MODEL=claude-3-opus-20240229
LLM_API_KEY=sk-ant-your-secure-key

# RAG Knowledge Ingestion Matrix
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_API_KEY=sk-your-secure-key

# Database Connectivity 
DATABASE_URL=postgresql+asyncpg://postgres:securepass@db-node-01:5432/deeptutor
```

**3. Fire Up Distributed Services**
```bash
docker compose up -d
```

### Frontend Compilation
To optimize web rendering via Vercel or isolated NodeJS runtimes:
```bash
cd web
npm install
npm run build 

# Engage the next production sequence
npm run start
```
---

## ⌨️ Command Line Extensibility (CLI)

Agent workflows do not require user interfaces. DeepTutor operates natively via API schemas and CLI arguments. You can inject external system commands or script automated curriculum generations via shell endpoints.

```bash
deeptutor run deep_solve "Compute the Fourier Transform eigenvalues" -t reason
deeptutor kb create advanced_physics --doc tensor_calculus.pdf 
deeptutor session list
deeptutor bot create mr-miyagi --persona "Philosophical, concise, relies on first principles"
```

---

<div align="center">

**[Engineered & Designed by Dhruv Shah with Claude AI]**

[⭐ View Projects](https://github.com/dhruvshah464) · [🐛 Issues & Requests](https://github.com/dhruvshah464/DeepTutor/issues)

</div>
