# Phronel AI Agent - User Guide

This guide describes the basic setup and operation of the Phronel AI Agent.

## 1. Installation and Initial Configuration

Please run this in an environment with Python 3.10 or higher installed.

```bash
# Create and activate a virtual environment (Recommended)
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Initial Setup Wizard

Before using the system for the first time, you must register your API keys.

```bash
python -m phronel_ai_agent init
```
Follow the prompts in your terminal to register the following:
1. **X (Twitter) API Keys**: Key set obtained from the X Developer Portal
2. **Gemini API Key**: API key for Google Gemini, used as the AI's "brain"
3. **Execution Mode**: Run mode (We recommend starting with `manual` or `dry-run`)

## 2. Switching Execution Modes
The agent monitors designated keywords, gathers information, and automatically creates draft posts.
You can control the level of autonomy by changing the execution mode using the configuration command.

```bash
# Safe simulation mode (no actual posts are sent to X API)
python -m phronel_ai_agent config execution_mode dry-run

# Semi-automatic mode (automatically creates drafts every 5 mins; requires manual approval to post)
python -m phronel_ai_agent config execution_mode semi-auto

# Fully automatic mode (100% autonomous; searches, strategizes, generates, and posts every 5 mins)
python -m phronel_ai_agent config execution_mode auto

# Changing the search keyword to monitor
python -m phronel_ai_agent config observe_keyword "Generative AI"
```

For more configuration parameters, please refer to [CONFIG_REFERENCE.md](./CONFIG_REFERENCE.md).

## 3. TUI (Terminal User Interface) Dashboard

Start the terminal dashboard to monitor the agent's real-time actions and approve draft proposals manually.

```bash
python -m phronel_ai_agent start
```

### Dashboard Tabs and Features
The TUI is divided into **four tabs** (which can be switched via mouse click or by using the arrow keys to focus navigation):

*   **Dashboard Tab**:
    *   **Live Log**: Real-time logging of keyword searches, AI strategizing, and background pipeline events.
    *   **Status Panel**: Displays the active mode and count of pending actions.
    *   **Manual Triggers**: Buttons to manually run `Observe` or `Propose` tasks.
*   **Action Review Tab**:
    *   List of pending draft posts (Actions) created by the AI.
    *   `Approve Selected`: Marks a draft as "approved".
    *   `Execute Selected`: Sends approved drafts directly to X (via Tweepy).
    *   `Reject Selected`: Deletes or rejects drafts.
*   **Knowledge Base Tab**:
    *   **Source List**: Left pane showing all ingested sources (files, URLs).
    *   **Source Content Preview**: Right pane showing interactive JIT text chunk previews of the selected source.
    *   **`[ + Learn Material (File/URL) ]` Button**: Opens a popup modal to enter local file paths or web URLs. It auto-detects and crawls the content immediately.
    *   **`[ Delete Selected ]` Button**: Synced deletion of the selected source from both SQLite and ChromaDB to prevent outdated information or hallucinations.
*   **Persona Settings Tab**:
    *   Visual CRUD editor for managing agent personas.
    *   **Registered Personas (Left Pane)**: Displays all configured personas and indicates which one is actively running (★ Active).
    *   **Edit Form (Right Pane)**: Update name, professional role, tone of voice, constraints, and sales strategy guidelines dynamically.
    *   **Control Buttons**: Save edits, create new templates, activate selected persona instantly, or safely delete inactive configurations.

### Keyboard Shortcuts
- `s`: Manually trigger one full autonomous cycle (Search ➔ Strategy ➔ Generate).
- `r`: Refresh all database views immediately.
- `q`: Exit the dashboard.

## 4. Ingesting Sales Materials (RAG Knowledge)

To guide the AI's content and ensure factual accuracy, you can import company documentation, specification files, or online web URLs.

### ① Ingesting Local Markdown/Text Files
```bash
python -m phronel_ai_agent learn ./docs/my_product_info.md
```
The text is automatically chunked and saved concurrently in ChromaDB and SQLite.

### ② Ingesting Web URLs
```bash
python -m phronel_ai_agent learn-url "https://example.com/product-specification"
```
Downloads the HTML content, intelligently strips out unnecessary elements (scripts, styles, footer elements), chunks the remaining text body, and saves it to the vector database.

### ③ Listing Ingested Sources
```bash
python -m phronel_ai_agent learn-list
```
Displays all learned sources, total chunks, and ingestion dates in a formatted Rich table.

### ④ Deleting a Source
```bash
python -m phronel_ai_agent learn-remove "./docs/my_product_info.md"
```
Sync-deletes the source from SQLite and ChromaDB to prevent the AI from quoting outdated material.
