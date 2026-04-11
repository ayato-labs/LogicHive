# 🏗️ LogicHive System Architecture

LogicHive is designed as a **Logic Orchestration Layer** that sits between high-intelligence AI Agents and persistent storage. Its primary goal is to solve the "Logic Rot" and "Memory Fragmentation" problems inherent in current RAG-based AI workflows.

## 1. High-Level Overview

LogicHive follows a "Post-RAG Paradigm" where the unit of retrieval is not a document, but a **Verified Logic Unit (VLU)**.

```mermaid
graph TD
    User([User]) <--> Agent[AI Agent / Antigravity]
    Agent <--> MCP[LogicHive MCP Server]
    
    subgraph Core ["LogicHive Core Engine"]
        Orchestrator[Orchestrator]
        EvalManager[Evaluation Manager]
        Storage[Storage Manager]
        
        subgraph Gate ["3-Tier Quality Gate"]
            DetLayer[Deterministic Verification]
            AILayer[AI Forensic Auditor]
            StaticLayer[Static Linter/Ruff]
        end
    end
    
    subgraph Persistence ["Persistent Vault"]
        Sqlite[(SQLite: Metadata)]
        Faiss[(FAISS: Vector Index)]
        GitHub[(GitHub: Remote Sync)]
    end

    MCP <--> Orchestrator
    Orchestrator --> EvalManager
    EvalManager --> Gate
    Gate -- "Verified [reliability_score >= 80]" --> Storage
    Storage <--> Persistence
```

---

## 2. The Validation Pipeline (Rigor Gate)

LogicHive implements a **Deterministic Veto** policy. Unlike naive AI-only evaluation, LogicHive enforces structural rigor before accepting "subjective" AI opinions.

```mermaid
sequenceDiagram
    participant Agent
    participant Orch as Orchestrator
    participant Det as Deterministic Layer
    participant AI as AI Layer
    participant Vault as Logic Vault

    Agent->>Orch: save_function(code, test_code)
    Orch->>Det: Audit Structural Rigor
    Note over Det: AST Analysis: check assertions & hollow logic
    
    alt is_hollow OR assertion_count == 0
        Det-->>Orch: Score 0 (REJECT)
        Orch-->>Agent: Fail: "Deterministic Rejection"
    else Rigor Passed
        Det-->>Orch: Base Score (e.g. 100)
        Orch->>AI: Holistic Review
        AI-->>Orch: Weighted Opinion
        Orch->>Vault: Persist with [reliability_score]
        Vault-->>Agent: Success: Logic Promoted
    end
```

---

## 3. Core Design Philosophies

### A. Facts over Opinions
We believe LLM evaluations are non-deterministic and can be prone to "Sophistry" (sounding correct but lacking substance). LogicHive uses **AST (Abstract Syntax Tree)** parsing to prove that:
- Tests actually exist (Assertion count).
- Code is not performative (Hollow method detection).

### B. Anti-Rot (Software Preservation)
Logic is a living asset. LogicHive includes background audit tools (`stabilize_vault.py`) that periodically re-verify assets against shifting runtime environments.

### C. Contextual Isolation
Multi-tenant security is built-in. Project metadata ensures that proprietary logic from Project A never leaks into the suggestion context of Project B, even within the same vector space.

---

## 🚀 Future Vision: Auto-Dev Factory
LogicHive is evolving from a storage hub to a **Self-Optimizing Factory**.
1. **Discovery**: Find legacy logic.
2. **Adaptation**: Auto-refactor unit to match current project context.
3. **Professionalization**: Auto-generate missing tests to promote logic to "Verified" status.
