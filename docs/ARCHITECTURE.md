# Phronel AI Agent - System Architecture & Code Map

This document is a comprehensive developer guide detailing the system architecture, database models, method mappings, and execution lifecycles for the **Phronel AI Agent**—the autonomous SNS sales representative.

---

## 1. Directory Structure

The project implements a clean layered architecture (4-tier system). This separation of concerns ensures low coupling, making unit testing and feature extensions straightforward.

```text
sns_agent/
├── .gitignore                   # Environmental and Git ignore configuration
├── .env.example                 # Environment variables setup template
├── .env                         # Local secret API keys and configuration settings
├── GEMINI.md                    # AI assistant context guidelines (private)
├── README.md                    # Project landing page & quickstart
├── requirements.txt             # Pip package dependencies
├── docs/                        # Public user manuals & references
│   ├── ARCHITECTURE.md          # [This Doc] Technical Architecture & Code Map
│   ├── ARCHITECTURE_JA.md       # Japanese version of the Technical Architecture
│   ├── index.md                 # English documentation landing page
│   ├── index_JA.md              # Japanese documentation landing page
│   ├── USER_GUIDE.md            # English installation & setup guide
│   ├── USER_GUIDE_JA.md         # Japanese installation & setup guide
│   ├── CONFIG_REFERENCE.md      # English config settings reference
│   └── CONFIG_REFERENCE_JA.md   # Japanese config settings reference
├── tests/                       # Automated test suites
│   ├── conftest.py              # Test harness and secure environment isolation
│   ├── test_db.py               # Database integration tests
│   ├── test_llm_logger.py       # LLM interaction logging tests
│   ├── test_metrics.py          # Evaluator and multi-tier metrics tests
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
    │       ├── __init__.py      # Package entry point
    │       ├── app.py           # Core TUI driver & real-time log stream
    │       ├── modals.py        # Dialog modals (Action details, import knowledge modal)
    │       ├── dashboard_view.py# Status summary widget & metrics visualization
    │       ├── review_view.py   # Draft review and action execution console
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
Tracks every action (tweets, replies, likes, follows) suggested by the AI or scheduled for review.
*   **`id` (Optional[int], PK)**: Auto-increment index.
*   **`action_type` (str)**: `'tweet'`, `'reply'`, `'like'`, or `'follow'`.
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
*   **`context_summary` (str)**: Summary of the situation (e.g., "Timeline analysis").
*   **`strategy_text` (str)**: Deep strategic reasoning generated by the AI's strategist module.
*   **`model_name` (str)**: Active LLM name (e.g., `gemini-2.5-flash`).
*   **`created_at` (datetime)**: Log timestamp.

### 2.5. AgentPersona
Stores the identity presets for hot-swapping AI characters.
*   **`id` (Optional[int], PK)**: Auto-increment index.
*   **`name` (str)**: Persona name (e.g., `"Phronel"`).
*   **`role` (str)**: Core profession/perspective (e.g., `"SNS Sales Rep..."`).
*   **`tone` (str)**: Character tone of voice (e.g., `"Professional, polite, helpful..."`).
*   **`constraints` (str)**: Negative rules and output constraints (e.g., `"Max 280 chars..."`).
*   **`sales_strategy` (str)**: Dynamic guidelines maps to DSPy parameters.
*   **`is_active` (bool)**: Status flag. The active record is loaded JIT to dictate the agent's personality.

---

## 3. Function & Method Map

This detailed map covers class signatures and operational descriptions across all application layers.

| Tier | Module / File | Class / Method | Signature | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Core** | `core/db.py` | `init_db` | `()` -> `None` | Initializes SQLite DB tables using SQLModel. |
| | | `get_session` | `()` -> `Session` | Yields/creates a new database session. |
| | | `get_actions_by_status` | `(statuses: List[str])` -> `List[ActionLog]` | Returns actions matching a list of statuses in reverse chronological order. |
| | | `get_pending_action_count` | `()` -> `int` | Returns count of `pending` draft actions in the database. |
| | | `update_action_status` | `(action_id: int, new_status: str)` -> `Optional[ActionLog]` | Updates and saves an action log status. |
| | | `get_active_persona` | `()` -> `AgentPersona` | Fetches the active persona; automatically generates default JIT if missing. |
| | | `save_active_persona` | `(name, role, tone, constraints, strategy)` -> `AgentPersona` | Saves or updates active persona settings in a single operation. |
| | | `list_personas` | `()` -> `List[AgentPersona]` | Returns all registered personas in SQLite. |
| | | `add_persona` | `(name, role, tone, constraints, strategy)` -> `AgentPersona` | Inserts a new persona record. |
| | | `update_persona` | `(id, name, role, tone, constraints, strategy)` -> `AgentPersona` | Updates the persona record matching the specified ID. |
| | | `delete_persona` | `(id)` -> `bool` | Deletes the persona record matching the specified ID (active personas are protected from deletion). |
| | | `activate_persona` | `(id)` -> `bool` | Activates the target persona and deactivates all others. |
| | `core/config.py` | `ConfigManager.get` | `(key: str, default: Optional[str])` -> `Optional[str]` | Fetches config from DB with fallback to environmental variable `PHRONEL_<KEY>`. |
| | | `ConfigManager.set` | `(key: str, value: str, description: Optional[str])` -> `AgentConfig` | Saves or updates config key-value pair in database. |
| **Services**| `services/knowledge.py` | `KnowledgeBase.__init__` | `(persist_directory: Optional[str])` | Prepares ChromaDB client and splitter for lazy JIT load. |
| | | `KnowledgeBase.add_document`| `(content: str, source: str)` -> `int` | Splits text into semantic chunks, indexing in ChromaDB and storing in SQLite. |
| | | `KnowledgeBase.add_url` | `(url: str)` -> `int` | Crawls URL, cleans HTML elements, and stores plain text in ChromaDB and SQLite. |
| | | `KnowledgeBase.list_sources`| `()` -> `List[Dict[str, Any]]` | Queries SQLite to list ingested knowledge sources, total chunks, and ingestion times. |
| | | `KnowledgeBase.get_chunks_by_source`| `(source: str)` -> `List[KnowledgeChunk]` | Retrieves all text chunks associated with a specific knowledge source. |
| | | `KnowledgeBase.delete_source`| `(source: str)` -> `int` | Synchronously deletes source chunks from both SQLite and ChromaDB. |
| | | `KnowledgeBase.query` | `(query_text: str, n_results: int)` -> `List[str]` | Queries ChromaDB for semantic matching context chunks to use as RAG context. |
| | `services/x_client.py` | `XClient.__init__` | `()` | Initializes internal authentication variables and flags. |
| | | `XClient._authenticate` | `()` -> `None` | Retrieves credentials from `ConfigManager` and initializes Tweepy clients (v2 and v1.1). Defaults to Mock mode if keys are missing. |
| | | `XClient.post_tweet` | `(text: str)` -> `Optional[dict]` | Publishes a tweet via the X API (prints to stdout in Mock mode). |
| | | `XClient.like_tweet` | `(tweet_id: str)` -> `Optional[dict]` | Likes a specified tweet on X. |
| | | `XClient.reply_to_tweet` | `(tweet_id: str, text: str)` -> `Optional[dict]` | Replies to a specific tweet on X. |
| | | `XClient.search_tweets` | `(query: str, max_results: int)` -> `Any` | Searches for recent tweets using relevant keywords. |
| | | `XClient.get_tweet_metrics`| `(tweet_ids: List[str])` -> `List[dict]` | Retrieves a batch of statistical metrics (likes, retweets, etc.) for a list of tweet IDs. |
| **Skills** | `skills/brain.py` | `Strategist.analyze_timeline`| `(tweets: List[str])` -> `Optional[dict]` | Analyzes tweets using DSPy CoT (`AnalyzeTrend` Signature) to formulate a strategy. |
| | | `Creator._get_knowledge` | `(topic: str)` -> `str` | Queries knowledge base for chunks related to a topic and compiles them into a single RAG context string. |
| | | `Creator.create_tweet` | `(strategy_insight: str, topic: str)` -> `str` | Generates a new tweet, dynamically injecting the active persona's name, role, tone, constraints, and sales strategy. |
| | | `Creator.create_reply` | `(target_tweet: str, strategy_insight: str, topic: str)` -> `str` | Generates a reply to a target tweet, dynamically injecting the active persona's configuration. |
| | | `Brain.__init__` | `()` | Initializes member variables. Defers (lazy loads) LLM configuration setup and few-shot prompt file loading. |
| | | `Brain._ensure_ready` | `()` -> `None` | Performs JIT initialization of the Gemini LLM configuration and loads few-shot prompts from disk upon the first inference call. |
| | | `Brain.process_and_propose`| `(source_data: list, context_summary: str)` -> `Optional[ActionLog]` | Complete cognitive pipeline: Analyzes observation data (list/str), merges the active persona context, generates and registers an action proposal, and links the resulting `ActionLog` and `StrategyLog` via foreign key. |
| | | `Brain.create_tweet_proposal`| `(topic: str)` -> `ActionLog` | Generates a new tweet draft based on a topic using RAG, and saves it in a `pending` state. |
| | `skills/observer.py` | `Observer.observe_keyword`| `(keyword: str, max_results: int)` -> `Optional[ActionLog]` | Searches X for a specific keyword and streams matching tweets (including tweet IDs and user IDs as metadata) into `Brain.process_and_propose` to propose autonomous actions. |
| | `skills/executor.py` | `execute_action` | `(action_id: int)` -> `Optional[ActionLog]` | Executes the specified action. If `execution_mode` is `dry-run`, simulates execution and logs output without calling the X API. Records success/failure state in the database. |
| | | `approve_action` | `(action_id: int)` -> `Optional[ActionLog]` | Updates an action's status from `pending` to `approved`. |
| | `skills/analyst.py` | `Analyst.generate_daily_report`| `(target_date: Optional[datetime])` -> `str` | Aggregates action logs, strategy logs, and engagement metrics from X for the day, and uses DSPy to generate a polished Markdown insight report. |
| | | `Analyst.optimize_creator_prompts`| `()` -> `bool` | Mines successful actions and their corresponding strategy logs from the SQLite database, compiles them into training examples, and runs the DSPy `BootstrapFewShot` optimizer to save optimized few-shot prompt configurations to disk. |
| | `skills/metrics.py` | `phronel_multi_tier_metric`| `(example, pred, trace)` -> `float` | **[Evaluation Layer]** Evaluates responses against guardrails (character limit of 280, empty checks, hallucination checks), aesthetic constraints (hashtag/emoji count limits), and semantic consistency with strategic goals using ChromaDB embeddings, returning a multi-tiered score between 0.0 and 1.0. |
| **Interfaces**| `interfaces/main.py` | CLI Commands | - | Provides commands (`start`, `init`, `config`, `learn`, `learn-list`, `learn-remove`, `learn-url`, `propose`, `observe`, `actions`, `approve`, `execute`, `report`, `optimize`) powered by Typer. |
| | `interfaces/tui/app.py` | `PhronelApp.compose` | `()` -> `ComposeResult` | Combines the header, footer, and the four view tabs (Dashboard, Action Review, Knowledge Base, Persona Settings) into the main TUI container. |
| | | `PhronelApp.on_mount` | `()` -> `None` | Securely registers the `TuiLogHandler` logging handler to prevent UI crashes and starts a periodic background polling job scheduled every 5 minutes. |
| | | `PhronelApp.update_ui_status`| `()` -> `None` | Synchronizes all views (Dashboard, Actions, RAG, Personas) with the latest database state. |
| | `interfaces/tui/modals.py`| `ActionDetailModal.compose`| `()` -> `ComposeResult` | Renders a modal popup displaying action details and execution metadata. |
| | | `KnowledgeImportModal.compose`| `()` -> `ComposeResult` | Renders a centered import dialog, coordinating automatic file path or URL detection. |
| | | `dashboard_view.py` | `AgentStatus.compose` | `()` -> `ComposeResult` | Constructs and updates the dashboard summary widget. |
| | | `review_view.py` | `ActionReview.compose` | `()` -> `ComposeResult` | Renders the action review queue (using a TUI DataTable) and binds approve/reject/execute button actions. |
| | | `knowledge_view.py` | `KnowledgeBaseView.compose`| `()` -> `ComposeResult` | Displays the knowledge source list (left side) and links to the high-performance raw chunk preview panel (right side, synchronized with `RowHighlighted`), plus buttons to trigger import/delete modals. |
| | | `persona_view.py` | `PersonaSettingsView.compose`| `()` -> `ComposeResult` | Renders the persona manager: list of personas (left side) and editable settings panel (right side) with save, delete, create, and activate handlers. |

---

## 4. Feature Execution Lifecycles (Feature-Function Mapping)

This section maps Phronel's core features to the execution order and collaboration of their supporting functions.

### 4.1. Setup & Authentication
This initialization step initializes the configuration database table (`AgentConfig`) and establishes credentials.
1. The user runs the `interfaces/main.py (init)` command or launches the TUI.
2. `core/db.py (init_db)` initializes the SQLite database and its tables.
3. The API keys and system variables input by the user are persisted via `core/config.py (ConfigManager.set)`.
4. At runtime, `services/x_client.py (XClient._authenticate)` is called, fetching credential keys through `ConfigManager.get`.
5. Tweepy clients are set up (automatically falling back to Mock mode if keys are missing).

```text
[User CLI] -> init() 
                 |
                 v
            init_db() -> SQLite Database Created
                 |
                 v
            ConfigManager.set() -> Save X & LLM API Keys
                 |
        (On First API call)
                 v
            XClient._authenticate() -> Setup Tweepy V2 / V1.1 client
```

### 4.2. Ingesting Knowledge (RAG)
Ingests and indexes user materials (such as Markdown or plain text files) and web URLs to enable highly accurate generation.
1. A source path or URL is provided via the `interfaces/main.py (learn)` / `(learn-url)` commands or TUI modal.
2. `services/knowledge.py (KnowledgeBase.add_document)` or `add_url` is invoked.
3. `RecursiveCharacterTextSplitter` segments the text into clean semantic chunks.
4. Chunks are registered in `ChromaDB` (the vector store).
5. Concurrently, the same chunk content is stored in the SQLite `KnowledgeChunk` table with source metadata.
6. During subsequent post and reply generation, `skills/brain.py (Creator._get_knowledge)` calls `KnowledgeBase.query` to semantically retrieve matching high-relevance chunks.

```text
[Markdown Document] -> phronel learn <path>
                             |
                             v
                 KnowledgeBase.add_document()
                             |
         +-------------------+-------------------+
         | (Vector Space)                        | (Relational database)
         v                                       v
    ChromaDB (PersistentClient)             SQLite (KnowledgeChunk table)
         |                                       |
         +-------------------+-------------------+
                             |
                   (During Content Generation)
                             v
                 KnowledgeBase.query() -> context chunks injected to DSPy prompt
```

### 4.3. Cognitive Pipeline (Observe ➔ Strategize ➔ Propose)
A recurring pipeline that monitors target trends and logs recommended action proposals to the database.
1. Triggered by a periodic background timer or manual command (`interfaces/main.py (observe)`).
2. `skills/observer.py (Observer.observe_keyword)` starts, retrieving target tweets using `services/x_client.py (XClient.search_tweets)`.
3. The retrieved tweets are piped to `skills/brain.py (Brain.analyze_timeline)`.
4. The `Strategist` module analyzes the context using DSPy Chain-of-Thought (`AnalyzeTrend` Signature) to determine the trend, sentiment, and the best tactical action (e.g., reply or tweet).
5. Strategic reasoning is documented and saved in SQLite as a `StrategyLog`.
6. `Creator` pulls relevant RAG context and injects the active persona to draft the final tweet or reply body.
7. The drafted action is saved to the SQLite `ActionLog` table in a `pending` state, strongly linked to the `StrategyLog` via a foreign key, and waits for user review.

```text
 [Trigger / Timer] -> Observer.observe_keyword()
                             |
                             v
                     XClient.search_tweets() -> Get tweets from X
                             |
                             v
                     Brain.analyze_timeline() 
                             | (uses CoT to derive sentiment, topic, action)
                             v
                     StrategyLog -> Logged to SQLite (Explain "Why" decisions are made)
                             |
                             v
                     Creator.create_tweet() / create_reply() -> Pulls RAG context
                             |
                             v
                     ActionLog -> Saved in SQLite with "pending" status
```

### 4.4. Review & Execution
Handles draft reviews and final publishing to X.
1. Users review proposed drafts using `interfaces/main.py (actions)` or the TUI Action Review view.
2. When approved, `skills/executor.py (approve_action)` updates the draft status to `approved`.
3. Invoking `skills/executor.py (execute_action)` triggers publication.
4. If `core/config.py (ConfigManager.get("execution_mode"))` is set to `dry-run`, real API calls are skipped, simulating execution logs safely.
5. In active modes (`manual`, `semi-auto`, `auto`), `services/x_client.py (XClient.post_tweet / reply_to_tweet / like_tweet)` publishes the action on X.
6. Upon successful publication, the draft status updates to `executed`, raw response payloads are written to `result_json`, and `executed_at` is timestamped.

```text
 [ActionLog: pending] -> TUI / CLI approval
                             |
                             v
                         approve_action() -> ActionLog: approved
                             |
                             v
                         execute_action()
                             |
                             +-----[execution_mode == 'dry-run']? 
                             |        |
                             |        v (Yes)
                             |     Simulate API payload -> ActionLog: executed (DRY-RUN)
                             |
                             +-----(No: Real post)
                                      |
                                      v
                                  XClient.post_tweet() -> Post to X
                                      |
                                      v (Success)
                                   Save Response JSON -> ActionLog: executed
```

### 4.5. Continuous Prompt Optimization (Analyst)
The analytical engine that visualizes performance metrics and powers autonomous self-optimization (PDCA cycle).
*   **Reporting (`phronel report` / TUI "Generate Report" button)**:
    1. `skills/analyst.py (Analyst.generate_daily_report)` is executed.
    2. Historical `ActionLog` (executed actions) and matching `StrategyLog` data for the specified day are gathered from SQLite.
    3. `services/x_client.py (XClient.get_tweet_metrics)` is called to retrieve live engagement metrics (likes, impressions, retweets).
    4. These statistics and insights are structured and fed to the DSPy `GenerateDailyReport` signature to create a polished, comprehensive Markdown performance report.

*   **Prompt Optimization (`phronel optimize` / TUI "Run Optimizer" button)**:
    1. `skills/analyst.py (Analyst.optimize_creator_prompts)` is executed.
    2. Successful high-engagement actions and their matching strategist reasoning are extracted from SQLite as successful demonstrations (Examples).
    3. Using the DSPy `BootstrapFewShot` compiler, the Creator's generation modules (such as the `GenerateTweet` signature) are optimized using these compiled examples.
    4. The highest-scoring compiled prompts are saved to `phronel_ai_agent/core/optimized_creator.json`.
    5. Upon subsequent application boots, `Brain._load_optimized_prompts` loads this optimized JSON automatically, continuously refining and improving the agent's performance.

```text
               (Optimization Triggered)
                           |
                           v
               Analyst.optimize_creator_prompts()
                           |
                           v
               BootstrapFewShot (DSPy Compiler) -> Trains using high-performing Action logs
                           |
                           v
               optimized_creator.json (Saves best few-shot demos to disk)
                           |
              (On Next App/Brain Boot)
                           v
               Brain._load_optimized_prompts() -> Auto-loads into Creator Module
```

---

This document is compiled based on the latest codebase of Phronel. Please consult and maintain this specification during future feature development and refactoring to ensure system consistency.
