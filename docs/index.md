# 🧠 Phronel AI Agent

> **Autonomous AI Agent for SNS Sales and Marketing Powered by DSPy & Local RAG**

Phronel is an open-source, resident AI agent that autonomously monitors and analyzes the timeline, formulates optimized sales strategies, and conducts high-quality interactions on X (Twitter).

[:octicons-arrow-right-24: Get Started](./USER_GUIDE.md){ .md-button .md-button--primary }
[:octicons-mark-github-16: View on GitHub](https://github.com/skzy2018/phronel-ai-agent){ .md-button }

---

## ✨ Key Features

!!! info "🧠 DSPy Self-Improving Prompt Loop"
    Say goodbye to manual prompt engineering. By parsing previous successful posts (Action Log) and the AI's logic (Strategy Log) directly from the database, Phronel automatically constructs and optimizes the most effective few-shot prompts for future runs.

!!! success "👥 Multi-Persona Management"
    Through the rich TUI (Terminal User Interface), you can dynamically manage and hot-swap multiple agent personas with distinct roles, tones of voice, sales strategies, and posting constraints.

!!! security "🔒 100% Local & High Security"
    All sensitive information, including API keys, sales materials, and interaction logs, is saved directly inside your local computer (SQLite / ChromaDB). Unlike typical cloud SaaS offerings, there is zero risk of data leakage.

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/skzy2018/phronel-ai-agent.git
cd phronel-ai-agent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initial Setup (API Key configuration)
python -m phronel_ai_agent init

# 5. Launch the TUI Dashboard
python -m phronel_ai_agent start
```
