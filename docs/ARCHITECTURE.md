# Phronel AI Agent - System Architecture & Code Map

This document is a comprehensive developer guide detailing the system architecture, database models, method mappings, and execution lifecycles for the **Phronel AI Agent**—the autonomous SNS sales representative.

---

## 1. Directory Structure

The project implements a clean layered architecture (4-tier system). This separation of concerns ensures low coupling, making unit testing and feature extensions straightforward.

```text
sns_agent/
├── GEMINI.md                    # AI assistant context guidelines (private)
├── README.md                    # Project landing page & quickstart
├── requirements.txt             # Pip package dependencies
├── docs/                        # Public user manuals & references
│   ├── ARCHITECTURE.md          # [This Doc] Technical Architecture & Code Map
│   ├── index.md                 # English documentation landing page
│   ├── index_JA.md              # Japanese documentation landing page
│   ├── USER_GUIDE.md            # English installation & setup guide
│   ├── USER_GUIDE_JA.md         # Japanese installation & setup guide
│   ├── CONFIG_REFERENCE.md      # English config settings reference
│   └── CONFIG_REFERENCE_JA.md   # Japanese config settings reference
├── tests/                       # Automated test suites
│   ├── conftest.py              # Test harness and secure environment isolation
│   ├── test_db.py               # Database integration tests
│   ├── test_observer.py         # Keyword tracking and parsing logic tests
│   └── test_phase1~4.py         # Phase-by-phase end-to-end integration tests
└── phronel_ai_agent/             # Core Python codebase
    ├── __init__.py              # Package initializer
    ├── __main__.py              # CLI executable entry point
    ├── core/                    # [Core Tier] Database & Config management
    │   ├── db.py                # Database connection & repository helpers
    │   ├── config.py            # Hybrid configuration manager (ConfigManager)
    │   └── models.py            # SQLite schemas defined via SQLModel
    ├── interfaces/              # [Presentation Tier] Terminal interfaces (TUI/CLI)
    │   ├── main.py              # Typer CLI commands
    │   └── tui/                 # Textual terminal UI package
    │       ├── app.py           # Core TUI driver
    │       ├── dashboard_view.py# System monitoring log stream & buttons
    │       ├── review_view.py   # Draft review and execution console
    │       ├── knowledge_view.py# Vector RAG management & visual previewer
    │       └── persona_view.py  # Persona settings visual form editor
    ├── services/                # [Infrastructure Tier] External APIs & ChromaDB
    │   ├── x_client.py          # Tweepy wrapper for X API (Online / Mock fallback)
    │   └── knowledge.py         # ChromaDB client & vector store integration (RAG)
    └── skills/                  # [Domain/Skill Tier] Autonomous Agent Logic
        ├── brain.py             # Strategic thinking core (DSPy modules)
        ├── observer.py          # Background trend scouter & parser
        ├── executor.py          # Action publisher (Tweets, Replies, Likes)
        ├── analyst.py           # Performance reporter & prompt compiler (Analyst)
        └── metrics.py           # Multi-tier quality evaluator for DSPy compiles
```

---

## 2. Data Models

All relational models are defined in `phronel_ai_agent/core/models.py` using `SQLModel` (inherits from SQLAlchemy/Pydantic) and are saved to the local SQLite database (`phronel_agent.db`).

### 2.1. AgentConfig
Key-Value store for system-wide variables (API keys, execution modes, keywords).
*   **`key` (str, PK)**: Config item key (e.g., `gemini_api_key`, `execution_mode`).
*   **`value` (str)**: Config value.
*   **`description` (Optional[str])**: Brief usage text.
*   **`updated_at` (datetime)**: Timestamp of last edit.

### 2.2. KnowledgeChunk
RAG chunks corresponding to vectors stored in ChromaDB.
*   **`id` (Optional[int], PK)**: Auto-increment index.
*   **`content` (str)**: Splitted text segment.
*   **`source` (str)**: Original file path or web URL source.
*   **`embedding_id` (Optional[str])**: Correlated vector ID inside ChromaDB.
*   **`created_at` (datetime)**: Timestamp of ingestion.

### 2.3. ActionLog
Tracks every action (tweets, replies, likes) suggested by the AI or scheduled for review.
*   **`id` (Optional[int], PK)**: Auto-increment index.
*   **`action_type` (str)**: `'tweet'`, `'reply'`, or `'like'`.
*   **`content` (Optional[str])**: Body text.
*   **`target_id` (Optional[str])**: Recipient tweet ID or user ID.
*   **`status` (str)**: Processing state (`pending`, `approved`, `executed`, `failed`).
*   **`strategy_log_id` (Optional[int])**: Foreign key linking directly to the decision logic (`StrategyLog`).
*   **`result_json` (Optional[str])**: API response payload in raw JSON format.
*   **`created_at` (datetime)**: Draft timestamp.
*   **`executed_at` (Optional[datetime])**: Successful publication timestamp.

### 2.4. StrategyLog
Stores the Chain-of-Thought (CoT) reasoning behind each decision, forming the basis for reports and DSPy optimization.
*   **`id` (Optional[int], PK)**: Auto-increment index.
*   **`context_summary` (str)**: Summary of the situation (e.g., "Keyword search: Generative AI").
*   **`strategy_text` (str)**: Deep strategic reasoning generated by the AI's strategist module.
*   **`model_name` (str)**: Active LLM name (e.g., `gemini-2.5-flash`).
*   **`created_at` (datetime)**: Log timestamp.

### 2.5. AgentPersona
Stores the identity presets for hot-swapping AI characters.
*   **`id` (Optional[int], PK)**: Auto-increment index.
*   **`name` (str)**: Persona name (e.g., `"Phronel"`).
*   **`role` (str)**: Core profession/perspective (e.g., `"SNS Sales Rep..."`).
*   **`tone` (str)**: Character tone of voice (e.g., `"Professional, helpful..."`).
*   **`constraints` (str)**: Negative rules and output constraints (e.g., `"Max 280 chars..."`).
*   **`sales_strategy` (str)**: Dynamic guidelines maps to DSPy parameters.
*   **`is_active` (bool)**: Status flag. The active record is loaded JIT to dictate the agent's personality.

---

## 3. Function & Method Map

| Tier | Module / File | Class / Method | Signature | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Core** | `core/db.py` | `init_db` | `()` -> `None` | Initializes SQLite DB tables using SQLModel. |
| | | `get_session` | `()` -> `Session` | Yields a new SQLite database session. |
| | | `get_actions_by_status` | `(statuses: List[str])` -> `List[ActionLog]` | Returns actions matching a list of statuses. |
| | | `get_pending_action_count` | `()` -> `int` | Returns count of `pending` draft actions. |
| | | `update_action_status` | `(action_id: int, new_status: str)` -> `Optional[ActionLog]` | Updates and saves an action log status. |
| | | `get_active_persona` | `()` -> `AgentPersona` | Fetches active persona; generates default JIT if missing. |
| | | `list_personas` | `()` -> `List[AgentPersona]` | Returns all registered personas in SQLite. |
| | | `activate_persona` | `(id)` -> `bool` | Activates target persona and deactivates others. |
| | `core/config.py` | `ConfigManager.get` | `(key: str, default: str)` -> `str` | Fetches config from DB with fallback to environmental variable `PHRONEL_`. |
| | | `ConfigManager.set` | `(key: str, value: str)` -> `AgentConfig` | Saves or updates config key-value in database. |
| **Services**| `services/knowledge.py` | `KnowledgeBase.__init__` | `(persist_directory: str)` | Prepares ChromaDB client and splitter for lazy JIT load. |
| | | `KnowledgeBase.add_document`| `(content: str, source: str)` -> `int` | Chunks text, indexing in ChromaDB and storing in SQLite. |
| | | `KnowledgeBase.add_url` | `(url: str)` -> `int` | Crawls URL, cleans HTML elements, and stores in RAG. |
| | | `KnowledgeBase.delete_source`| `(source: str)` -> `int` | Synced deletion of source chunks from SQLite and ChromaDB. |
| | | `KnowledgeBase.query` | `(query_text: str, n_results: int)` -> `List[str]` | Queries ChromaDB for semantic matching context chunks. |
| | `services/x_client.py` | `XClient._authenticate` | `()` -> `None` | Prepares Tweepy clients; defaults to Mock mode if keys are missing. |
| | | `XClient.post_tweet` | `(text: str)` -> `Optional[dict]` | Publishes a tweet on X (prints to console in Mock mode). |
| | | `XClient.reply_to_tweet` | `(tweet_id: str, text: str)` -> `Optional[dict]` | Replies to a specific tweet on X. |
| **Skills** | `skills/brain.py` | `Strategist.analyze_timeline`| `(tweets: List[str])` -> `Optional[dict]` | Analyzes tweets using DSPy CoT (`AnalyzeTrend` Signature). |
| | | `Creator.create_tweet` | `(strategy_insight: str, topic: str)` -> `str` | Injects dynamic active persona and RAG to write a tweet. |
| | | `Brain._ensure_ready` | `()` -> `None` | JIT setups Gemini API configurations and loads saved prompts. |
| | | `Brain.process_and_propose`| `(source_data: list, context: str)` -> `Optional[ActionLog]` | Complete cognitive pipeline: Analyze ➔ Persona Injection ➔ Propose. |
| | `skills/metrics.py` | `phronel_multi_tier_metric`| `(example, pred, trace)` -> `float` | Multi-tier scored evaluator checking text length, emojis, hashtags, and ChromaDB cosine similarity. |
| **Interfaces**| `interfaces/tui/app.py` | `PhronelApp.update_ui_status`| `()` -> `None` | Synchronizes all views (Actions, RAG, Personas) with DB. |

---

## 4. Feature Execution Lifecycles

### 4.1. Setup & Authentication
1. User invokes `python -m phronel_ai_agent init` to register credentials via `ConfigManager.set`.
2. When the app boots, `XClient._authenticate` loads credentials. If keys are missing, the client boots into a secure, offline **Mock Mode** automatically.

### 4.2. Ingesting Knowledge (RAG)
1. CLI/TUI calls `KnowledgeBase.add_document` or `add_url`.
2. Text is split into clean semantic chunks and indexed concurrently in **ChromaDB** and **SQLite**.
3. During generation, `Creator._get_knowledge` queries ChromaDB to pull these chunks into the LLM context.

### 4.3. Cognitive Pipeline (Observe ➔ Strategize ➔ Propose)
1. Observer pulls timeline tweets using `XClient.search_tweets`.
2. These tweets are evaluated by the `Strategist` using DSPy.
3. The derived tactical insights are saved to SQLite as a `StrategyLog`.
4. `Creator` pulls RAG contextual chunks and injects the active dynamic `AgentPersona` to generate a high-quality post.
5. The post is saved to SQLite as a `pending` draft in `ActionLog`, tied to the `StrategyLog` via foreign key.

### 4.4. Review & Execution
1. TUI/CLI displays `pending` drafts.
2. Clicking `Approve` changes status to `approved`.
3. Clicking `Execute` triggers `execute_action`. If the system is in `dry-run` mode, it mimics output safely. If in active modes, it publishes directly via `XClient` and marks the database log as `executed`.

### 4.5. Continuous Prompt Optimization (Analyst)
1. The `Analyst` executes prompt compilation.
2. It queries high-performing `ActionLog` records and matching `StrategyLog` reasoning.
3. It compiles these into `dspy.Example` data points, invoking DSPy's `BootstrapFewShot` compiler.
4. The compiled, highest-scoring prompts are saved to `optimized_creator.json` and JIT-loaded on subsequent boots.
