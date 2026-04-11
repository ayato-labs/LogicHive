![CD Pipeline](https://github.com/Ayato-AI-for-Auto/LogicHive/actions/workflows/cd.yml/badge.svg)
# 🛡️ LogicHive: Reusable Logic Infrastructure

> **"Stop rebuilding the same logic. Build a long-term intelligence asset."**

LogicHive is a professional-grade **Logic Orchestration Layer** designed to liberate developers from repetitive implementation labor. It enables AI agents (Antigravity, Cursor, Gemini) to store, verify, and instantly reuse high-quality logic units across projects.

---

## 💎 What this portfolio proves

This project is NOT just a code storage tool. It is a demonstration of:
- **System Architecture**: Designing multi-layered validation pipelines for AI-generated code.
- **Production-Grade Rigor**: Implementing **Deterministic Verification** (AST analysis) to veto non-factual AI opinions.
- **Agentic Ecosystem Design**: Building infrastructure that makes LLMs truly autonomous and data-driven.

If you are evaluating for **AI Architect**, **Tech Lead**, or **LLM System Design** roles:  
👉 **Start here: [5-Minute Architecture Overview](ARCHITECTURE.md)**

---

## 🌟 Core Pillars

### 1. The Rigor Gate (3-Tier Quality Gate)
LogicHive uses a weighted scoring system (4:3:2:1) to promote code to "Verified" status.
- **Fact Layer (40%)**: Deterministic AST analysis. Zero assertions = Zero score. Mandatory veto power.
- **Static Layer (30%)**: Industrial-grade linting via Ruff and Radon complexity analysis.
- **AI Layer (20%)**: Forensic auditing by LLMs (Gemini 1.5 Pro) to detect "Logic Smells."
- **Execution Layer (10%)**: Managed runtime validation in isolated sandboxes.

### 2. High-Secure Sandbox Execution
Features the `EphemeralPythonExecutor` for zero-trust code verification.
- **Network Isolation**: Physical blockage via `uv --offline`.
- **Environment Scrubbing**: Prevents leakage of host environment variables or API keys.
- **Dynamic Dependency Resolution**: Auto-provisions environments on-the-fly.

### 3. Post-RAG Multi-Tenant Isolation
Moving beyond simple document RAG, LogicHive provides strict logic isolation.
- **Logic Scoping**: (Project, Name) composite indexing ensures Project A's IP never leaks into Project B's context.
- **Hybrid Storage**: Blazing fast retrieval using SQLite (WAL) and FAISS CPU.

---

## 🚀 Quick Setup

LogicHive is built on `uv` for 1-command professional environment setup.

```powershell
# 1. Install dependencies
uv pip install -e .

# 2. Register MCP Server
uv run src/mcp_server.py
```

---

## 🇯🇵 日本語サマリー (Japanese Summary)

LogicHiveは、開発者を「仕様の再構築」や「冗長な実装」から解放するための**プロフェッショナル向けプライベート・ロジック・ハブ**です。

### 核心的な価値
- **死んだコードの撲滅**: 「以前書いたはず」を無くし、AIエージェントが即座に再利用できる「検証済みロジック」を蓄積します。
- **屁理屈（Sophistry）の排除**: AIが「良さそう」と言っても、テストコード（Assertion）が不足していれば強制的に却下する「決定論的品質ゲート」を搭載。
- **巨人の肩に乗る開発**: 書けば書くほど自分の開発環境が強化される、自己増殖型のエンジニアリング資産を構築します。

---

## 🤝 Community & Support

Support the vision of "Liberation from human work through AI."
[🛡️ Join the Discord Community / Support via OFUSE](https://ofuse.me/21cfc1d2)

---

## 📄 License

LogicHive is released under the **PolyForm Shield License 1.0.0**. Professional use is encouraged; competitive service provision is restricted. See [LICENSE](LICENSE) for details.
