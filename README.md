# LogicHive: Multi-Tenant Context Management Hub for AI Agents

> **Status: Archived / Portfolio Showcase**
> *This project was developed over 3 weeks as a B2B SaaS MVP. While fully functional, it has been frozen to pivot towards B2C AI content automation. [Read the full story here](docs/blog/why_indie_devs_should_avoid_b2b_in_ai_era.md).*

LogicHive is a high-performance, secure, and multi-tenant infrastructure designed to solve the "context amnesia" problem in AI agents. It provides a long-term memory layer using the Model Context Protocol (MCP), allowing AI agents to persist, search, and recall structured logic and context across different sessions and organizations.

## 🚀 Key Features

- **Model Context Protocol (MCP) Integration**: Native support for the MCP standard, enabling any MCP-compatible agent (like Cursor, Claude Desktop) to connect to the hive.
- **Zero-Trust Security**: AST-based static code analysis to prevent sensitive data leaks and unauthorized system calls.
- **Multi-Tenant Architecture**: Robust organization-based isolation with custom quotas and tiered access.
- **Enterprise Billing**: Fully integrated with Stripe for subscription management and automated seat-based billing.
- **Advanced Persistence**: Hybrid storage using Supabase (PostgreSQL) for metadata and pgvector for semantic search.

## 🛠 Tech Stack

- **Backend**: Python 3.11+, FastAPI (Async API)
- **Database**: Supabase (PostgreSQL), DuckDB (Local caching)
- **Security**: Python AST for static analysis, JWKS for Zero-Trust verification
- **Deployment**: Google Cloud Run (Stateless Hub), Docker
- **Client**: MCP Server (TypeScript Bridge & Python Core)

## 📁 Repository Structure

```
LogicHive/
├── hub/               # Private Hub Backend (Cloud Run)
│   ├── api/           # Organization & User endpoints
│   ├── core/          # Security, Auth, and Models
│   └── scripts/       # Maintenance and DB migrations
├── edge/              # MCP Server Implementation
│   ├── backend/       # Python core for context sync
│   └── dev_tools/     # Security audit & testing tools
└── docs/              # Architecture, Strategy, and Design papers
```

## 🧠 Why was this project frozen?

Building a B2B tool in the rapidly evolving AI landscape is high risk. As LLM context windows expand (reaching 1M+ tokens in Gemini), the "middle-layer" tools for context management are being absorbed into the base models. 

This project stands as a testament to high-quality system design, zero-trust security implementation, and the ability to leverage cutting-edge protocols like MCP.

## 📄 License

This project is licensed under the MIT License.
