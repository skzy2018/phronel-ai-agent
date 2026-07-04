# Technical Architecture & Modern Design

Phronel is not just a practical tool; it is a showcase of the modern AI and Python ecosystem, built to satisfy developers who appreciate elegant, robust, and clean code.

---

## 1. Technology Stack

### 🧠 LLM Orchestration: DSPy Framework
We have completely rejected brittle, hard-coded string formatting templates for prompts, opting instead for **DSPy**:
*   **Signatures & Modules**: High-level semantic interfaces like `AnalyzeTrend`, `GenerateTweet`, and `GenerateReply` map abstract inputs to outputs. The orchestrating `Strategist` and `Creator` modules ensure structured, reliable model interaction.
*   **Few-Shot Compiling**: Employs DSPy optimizers to scan the local database for historical successes, compiling the best contextual demos dynamically on demand.

### 🖥️ User Interface: Textual (TUI)
Phronel sports a gorgeously styled terminal console using **Textual**, ensuring a rich, mouse-clickable graphical experience directly inside your SSH session or command prompt:
*   **Dashboard Tab**: Displays a live log stream from the agent's background schedules.
*   **Action Review Tab**: Lets you review pending drafts, approving (Approve) or publishing (Execute) them with single clicks.
*   **Knowledge Base Tab**: Manages vector sources, showing a real-time scrollable text chunk preview of what the RAG knows.
*   **Persona Settings Tab**: Easily update agent names, professional expertise, tone constraints, and strategy policies.

### 📊 Local Data Layers
*   **SQLite + SQLModel**: Stores configurations, action timelines, strategy logs, and persona settings in a single file (`phronel_agent.db`). Strong foreign-key integrity (ActionLog ➔ StrategyLog) traces every action back to its strategic rationale.
*   **ChromaDB**: An ultra-fast local vector store indexing chunks of Markdown files or scraped web pages, providing local semantic search capabilities without cloud dependencies.

---

## 2. Architectural Highlights

```text
  [ User Interface (TUI / CLI) ]
               │  ▲  (SQLModel / JIT Load)
               ▼  │
     [ SQLite (SQLModel) ]  ◄───►  [ ChromaDB (Vector Store) ]
               │                           ▲  (Semantic Query)
               ▼  (Retrieve & Inject)      │
     [ Brain Core (DSPy Module) ] ─────────┘
               │
               ▼  (Execute via Tweepy)
         [ X API (Twitter) ]
```

### JIT (Just-In-Time) Lazy Ingestion
To eliminate start-up overhead and prevent warnings when environment variables are missing (such as during system initialization or unit tests), both ChromaDB and LLM clients employ lazy initialization. Resources are connected only when a cognitive request is executed, ensuring a lightweight footprint.
