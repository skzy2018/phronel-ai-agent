# Phronel AI Agent

Phronel is an autonomous, resident "SNS Sales Representative" AI agent that handles information gathering, strategy formulation, and drafting/posting on X (Twitter) end-to-end.

Unlike traditional static tweet bots, Phronel uses **DSPy** (the programming-not-prompting framework for LLMs) to **observe** the environment, formulate custom **strategies** based on context and target KPIs, and **generate** highly relevant, context-aware posts and replies with a distinct persona.

---

## Key Features

- 🧠 **Cognitive Agent (DSPy-Powered)**: Leverages LLMs (like Google Gemini) to analyze trend sentiments, determine strategic angles, and output optimal actions (Tweet, Reply, Like, or Standby) tied directly to real tweet IDs.
- 👥 **Multi-Persona Settings (SQLModel)**: Offers a dedicated `AgentPersona` database table. Easily register, edit, and swap multiple characters (names, roles, tones, posting constraints, and sales guidelines) visually from the TUI.
- 📊 **RAG Knowledge Base (ChromaDB + Web Crawler)**: Ingests local Markdown/Text files or scrapes any public URL to strip away HTML noise and crawl pure article content into a local Vector Database (ChromaDB).
- 🖥️ **Rich Terminal User Interface (TUI)**: A beautiful console dashboard powered by Textual:
  - **Dashboard Tab**: Real-time log streamer and background scheduler monitors.
  - **Action Review Tab**: Review, approve (Approve), and publish (Execute) AI-generated proposals.
  - **Knowledge Base Tab**: Manage ingested sources, scroll-preview text chunks dynamically, and prune old information.
  - **Persona Settings Tab**: Dynamically configure and hot-swap active agent personalities.
- ⚙️ **Flexible Execution Modes**:
  - Supports `manual` (interactive), `semi-auto` (propose automatically, post manually), `auto` (fully autonomous), and `dry-run` (simulated execution without API expenses).
  - Implements a hybrid config hierarchy prioritizing database settings over environment variables.

---

## Quick Start

### 1. Installation
Ensure you have Python 3.10 or higher installed.

```bash
git clone https://github.com/sekizimataisuke/sns_agent.git
cd sns_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Settings
Copy `.env.example` to `.env` and fill in your keys. (Phronel automatically boots into a secure Mock mode if keys are missing, allowing safe local testing without API access)
```bash
cp .env.example .env
```

### 3. Setup Wizard (Optional API Registration)
```bash
python -m phronel_ai_agent init
```

### 4. Launch the TUI Dashboard
```bash
python -m phronel_ai_agent start
```

---

## Documents

For deeper implementation details, consult:
- [User Guide](./docs/USER_GUIDE.md) / [User Guide (JA)](./docs/USER_GUIDE_JA.md)
- [Configuration Reference](./docs/CONFIG_REFERENCE.md) / [Configuration Reference (JA)](./docs/CONFIG_REFERENCE_JA.md)
- [System Architecture & Code Map](./docs/ARCHITECTURE.md) / [System Architecture & Code Map (JA)](./docs/ARCHITECTURE_JA.md)
