# Phronel AI Agent - Configuration Reference

All settings for Phronel are stored in a local SQLite database and can be viewed or updated via the CLI command `phronel config`.

## Viewing and Modifying Settings

### To View a Single Setting
```bash
python -m phronel_ai_agent config <KEY>
```
Example: `python -m phronel_ai_agent config execution_mode`

### To Modify a Single Setting
```bash
python -m phronel_ai_agent config <KEY> <VALUE>
```
Example: `python -m phronel_ai_agent config observe_keyword "Python Development"`

---

## Supported Configuration Keys

### Core Settings & Run Modes
| Key | Default Value | Description |
| :--- | :--- | :--- |
| `execution_mode` | `manual` | Determines the agent's level of autonomy:<br>- `manual`: Background schedules do not run.<br>- `semi-auto`: Gathers trends and proposes draft posts every 5 minutes; posting requires manual approval in the TUI.<br>- `auto`: 100% autonomous workflow from search to publishing posts.<br>- `dry-run`: Simulation mode. Creates proposals but does not send requests to the actual X API. |
| `observe_keyword` | `AI エージェント` | The keyword target used by the Observer during timeline searches. |

### X (Twitter) API Credentials
API keys registered during the initial setup wizard (`python -m phronel_ai_agent init`).
Obtain these keys from your X Developer Portal.

| Key | Description |
| :--- | :--- |
| `x_api_key` | Consumer Key (API Key) |
| `x_api_secret` | Consumer Secret (API Secret) |
| `x_bearer_token` | OAuth 2.0 Bearer Token (Optional, but recommended) |
| `x_access_token` | Access Token |
| `x_access_token_secret` | Access Token Secret |

### AI Model (DSPy / LLM) Settings
Credentials and configurations for the AI's "brain".

| Key | Description |
| :--- | :--- |
| `gemini_api_key` | API Key for Google Gemini. If left unset, Phronel defaults to a secure "mock" offline mode. |

---

## 4. Hybrid Environment Variables (.env)

Phronel supports configuration via environment variables (or a local `.env` file). 
Some run-time configurations, such as `execution_mode` and `observe_keyword`, utilize a **hybrid priority model** where any user-configured TUI/CLI database values override the environmental variables, and variables are only used as fallback defaults.

### Available Variables (PHRONEL_ Prefix)

| Variable Name | Default Value | Description (Management Layer) |
| :--- | :--- | :--- |
| **`PHRONEL_DB_PATH`** | `phronel_agent.db` | **Infrastructure**: File system path for the SQLite database. |
| **`PHRONEL_CHROMA_DIR`** | `./chroma_db` | **Infrastructure**: Storage directory for ChromaDB vector embeddings. |
| **`PHRONEL_LLM_MODEL`** | `gemini-2.5-flash` | **Infrastructure**: Default Google Gemini model used for inference. |
| **`PHRONEL_OPTIMIZED_PROMPT_PATH`** | `phronel_ai_agent/core/optimized_creator.json` | **Infrastructure**: Local JSON path where DSPy-optimized prompts are loaded/saved. |
| **`PHRONEL_EXECUTION_MODE`** | `manual` | **Hybrid**: Fallback execution mode if not found in the SQLite DB. |
| **`PHRONEL_MAX_RESULTS`** | `10` | **Infrastructure**: Limit on how many tweets to fetch from X per search loop to control API cost. |
| **`PHRONEL_GEMINI_API_KEY`** | `None` | **Credential**: Gemini API Key (takes precedence over the db `gemini_api_key` setting). |
| **`PHRONEL_X_BEARER_TOKEN`** | `None` | **Credential**: X OAuth 2.0 Bearer Token. |
| **`PHRONEL_X_API_KEY`** | `None` | **Credential**: X API Key (Consumer Key). |
| **`PHRONEL_X_API_SECRET`** | `None` | **Credential**: X API Secret (Consumer Secret). |
| **`PHRONEL_X_ACCESS_TOKEN`** | `None` | **Credential**: X Access Token. |
| **`PHRONEL_X_ACCESS_TOKEN_SECRET`** | `None` | **Credential**: X Access Token Secret. |

---

## 5. Agent Persona Table (`AgentPersona`)

To separate system infrastructure configs from dynamic AI personas, character data is managed in an independent database table: **`AgentPersona`**.
You can perform visual CRUD actions on these records via the TUI's "Persona Settings" tab.

### Schema Fields

| Column Name | Data Type | Default Value | Description & Prompt Mapping |
| :--- | :--- | :--- | :--- |
| **`id`** | `INTEGER` (PK) | Auto-increment | Unique identifier. |
| **`name`** | `VARCHAR` | `"Phronel"` | AI's name. Injected into prompts as `Identity: You are '{name}'`. |
| **`role`** | `VARCHAR` | `"SNS Sales Rep..."` | AI's professional title. Blended into context definition. |
| **`tone`** | `VARCHAR` | `"Professional, ..."` | Tone of voice. Maps to DSPy's `style` parameter, controlling emojis and phrasing. |
| **`constraints`** | `VARCHAR` | `"Max 280 chars..."` | Formatting and length limits. Maps to DSPy's `constraints` parameter. |
| **`sales_strategy`**| `VARCHAR` | `"Focus on value..."` | Core business strategy and policy guidelines. Maps to DSPy's `strategy` parameter. |
| **`observe_keyword`**| `VARCHAR` | `None` | Comma-separated search keywords (e.g. `AI, Python, LLM`) used dynamically during trend monitoring. |
| **`is_active`** | `BOOLEAN` | `True` / `False` | Activation flag. The active persona is fetched dynamically at runtime via `get_active_persona()`. |

---

## 6. Persona & Knowledge Link Table (`PersonaSourceLink`)

To support N:N RAG knowledge relationships where multiple personas can freely share or separate specific resources (files/URLs), authorized knowledge links are managed in an independent junction table: **`PersonaSourceLink`**.

### Schema Fields

| Column Name | Data Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| **`persona_id`** | `INTEGER` (PK, FK) | None | Foreign key linking to `AgentPersona.id`. |
| **`source`** | `VARCHAR` (PK) | None | Unique string representing the file path or web URL source name. |

At runtime, ChromaDB is dynamically queried with an `$in` metadata filter on `source` matching the currently authorized list from this table, preventing cross-persona RAG hallucinations.
