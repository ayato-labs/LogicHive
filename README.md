![CD Pipeline](https://github.com/Ayato-AI-for-Auto/LogicHive/actions/workflows/cd.yml/badge.svg)
# 🛡️ LogicHive: Reusable Logic Infrastructure

> **"Stop rebuilding the same logic. Build a long-term intelligence asset."**  
> **哲学：巨人の肩の上に乗り、真に価値ある創造に集中せよ。**

LogicHive is a professional-grade **Logic Orchestration Layer** that sits between AI agents (Antigravity, Cursor, Gemini) and your persistent knowledge vault. It doesn't just store code; it stabilizes and verifies it.

---

## 💎 What this portfolio proves

This project demonstrates the transition from "Document-RAG" to "**Logic-RAG**":
- **System Architecture**: Designing multi-layered validation pipelines for AI-generated code.
- **Production-Grade Rigor**: Implementing **Deterministic Verification** (AST analysis) to veto non-factual AI opinions.
- **Agentic Ecosystem Design**: Integrating MCP (Model Context Protocol) with secure runtime sandboxes.

👉 **Architecture & Battle-Tested Lessons: [ARCHITECTURE.md](ARCHITECTURE.md)**

---

## 🧠 Philosophy: Logic over Sophistry (屁理屈に論理で抗う)

AI agents excel at creating code that *looks* correct (Sophistry). LogicHive is built on the belief that **"Opinion without proof is noise."**

### 🚫 What we give up (あきらめるもの)
- **Reliance on Memory**: We give up the wasted time of "I think I wrote this before."
- **Naive AI Trust**: We give up relying on LLM self-evaluation. AI is the *adapter*, not the *judge*.
- **Visual Fluff**: We give up premium UI for a technical MCP-first core that powers other AI tools.

### ✨ What we seek (求めるもの)
- **Reusable Atoms**: Storing only the "Atomic Logic" that has been structurally verified.
- **Anti-Rot (Software Preservation)**: Ensuring code works today, and will work tomorrow via automated auditing.
- **Strategic Leverage**: Starting every project from "One step ahead" by standing on the shoulders of your past work.

---

## 🏗️ The Rigor Gate: A War Story

We didn't just build a Quality Gate; we fought for it. LogicHive's 3-tier validation is the result of 3 rounds of failure:
- **Round 1**: Asked AI to check tests. *Result: AI gave 100% to `assert True`.*
- **Round 2**: Made the AI "Hostile." *Result: AI was fooled by complex-looking identity functions.*
- **Round 3 (Current)**: **Hybrid Deterministic Gate.** We use **AST Parsing** to count assertions and detect "Hollow Logic" before the AI even sees the code.

**Weighted Scoring (4:3:2:1):**
- **Fact (40%)**: AST analysis. Mandatory veto power.
- **Static (30%)**: Ruff/Radon metrics.
- **AI (20%)**: Forensic auditing.
- **Execution (10%)**: Isolated runtime validation.

---

## 🤖 Operation Cycle (運用サイクル)

1. **Discovery (探索)**: Find logic atoms via LogicHive MCP.
2. **Retrieval (抽出)**: Inject verified logic into the agent context.
3. **Adaptation (適合)**: AI refactors logic to match current namespaces.
4. **Professionalization (資産化)**: Refined logic is saved back.
5. **Stabilization (安定化)**: Background tools re-verify assets 24/7.

---

## 🐘 Handling Heavy AI Assets (Torch, Sklearn)

Registering code that imports large libraries like `torch` or `sklearn` can hit the **20s Quality Gate Timeout**. To bypass this and maintain a fast development rhythm, use the following patterns:

### 1. Lazy Import (Recommended)
Move heavy imports inside your functions. This prevents the library from loading during the initial module-level scan by LogicHive's AST analyzer.

```python
def perform_clustering(data):
    from sklearn.cluster import KMeans  # Lazy Import
    model = KMeans(n_clusters=3)
    return model.fit_predict(data)
```

### 2. Smart Mocking
If you must have top-level imports, use the `mock_imports` parameter in `save_function`. LogicHive will inject `MagicMock` for those modules during verification, allowing the logic structure to be validated without loading the actual library weight.

```python
# LogicHive will mock 'torch' if provided in mock_imports list
import torch

def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"
```

---

## 🚀 Quick Setup

```powershell
# 1. Install dependencies
uv pip install -e .

# 2. Register MCP Server
uv run src/mcp_server.py
```

---

## 🇯🇵 日本語サマリー (Japanese Summary)

LogicHiveは、「仕様の再構築」や「冗長な実装」から開発者を解放するための**プロフェッショナル向けプライベート・ロジック・ハブ**です。

### 核心的な価値
- **死んだコードの撲滅**: 良質なロジックを「共有知」へ。
- **決定論的品質ゲート**: AIの温情を排し、AST解析（事実）が品質を担保する。
- **巨人の肩に乗る**: 書けば書くほど自分の開発環境が強化される「知の資産化」。

---

## 📄 License & Community
Released under **PolyForm Shield License 1.0.0**. Professional use encouraged.  
[🛡️ Join the Community / Support via OFUSE](https://ofuse.me/21cfc1d2)
