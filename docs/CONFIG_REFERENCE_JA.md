# Phronel AI Agent - Configuration Reference

Phronelの設定はSQLiteデータベースに保存され、CLIコマンド `phronel config` を用いて閲覧・変更することができます。

## 設定の確認と変更

### 1つの設定を確認する
```bash
python -m phronel_ai_agent config <KEY>
```
例: `python -m phronel_ai_agent config execution_mode`

### 1つの設定を変更する
```bash
python -m phronel_ai_agent config <KEY> <VALUE>
```
例: `python -m phronel_ai_agent config observe_keyword "Python 開発"`

---

## サポートされている設定キー一覧

### 基本設定・運用モード
| キー | デフォルト値 | 説明 |
| :--- | :--- | :--- |
| `execution_mode` | `manual` | エージェントの自律動作のレベルを決定します。<br>- `manual`: バックグラウンドタスクは実行されません。<br>- `semi-auto`: 5分ごとの定期実行で情報収集と提案（Pending）を行いますが、投稿には手動の承認が必要です。<br>- `auto`: 情報収集からXへの実際の投稿までを全自動で実行します。<br>- `dry-run`: 投稿のシミュレーションのみを行い、X APIにはリクエストを送信しません。 |
| `observe_keyword` | `AI エージェント` | Xのタイムラインや検索機能（Observe）で、情報収集の対象とするキーワードです。 |

### X (Twitter) API 認証情報
初期設定時に `python -m phronel_ai_agent init` で登録されるAPIキー群です。
これらはX Developer Portalから取得したものを設定します。

| キー | 説明 |
| :--- | :--- |
| `x_api_key` | Consumer Key (API Key) |
| `x_api_secret` | Consumer Secret (API Secret) |
| `x_bearer_token` | OAuth 2.0 Bearer Token (必須ではありませんが推奨) |
| `x_access_token` | Access Token |
| `x_access_token_secret` | Access Token Secret |

### AI モデル (DSPy / LLM) 設定
エージェントの「脳」として機能するLLMの認証情報です。

| キー | 説明 |
| :--- | :--- |
| `gemini_api_key` | Google Gemini APIを利用するためのキーです。未設定の場合、モック（ダミー）モードで動作します。 |

---

## 4. ハイブリッド環境変数一元管理 (.env) [新規追加!]

Phronelは、インフラ・システム基本設計に関する設定を環境変数（または `.env` ファイル）で定義できます。
さらに、実行モードや検索キーワードなどの一部の設定は、「ユーザーがTUIやCLIで動的設定した値」を最優先し、DBが未設定時の初期デフォルトシード値として環境変数（`.env`）からフォールバック読み込みする**ハイブリッド優先度モデル**を採用しています。

### 環境変数一覧 (PHRONEL_ プレフィックス)

| 環境変数名 | デフォルト値 | 説明 (管理レイヤー) |
| :--- | :--- | :--- |
| **`PHRONEL_DB_PATH`** | `phronel_agent.db` | **インフラ設定**: SQLiteデータベースファイルの物理保存パス。 |
| **`PHRONEL_CHROMA_DIR`** | `./chroma_db` | **インフラ設定**: ChromaDB ベクトルストアの物理保存先フォルダ。 |
| **`PHRONEL_LLM_MODEL`** | `gemini-2.5-flash` | **インフラ設定**: 推論に使用する Google Gemini のデフォルトモデル名。 |
| **`PHRONEL_OPTIMIZED_PROMPT_PATH`** | `phronel_ai_agent/core/optimized_creator.json` | **インフラ設定**: DSPyオプティマイザで自己生成した Few-shot プロンプトデータの保存/読込先パス。 |
| **`PHRONEL_EXECUTION_MODE`** | `manual` | **ハイブリッド**: エージェントのデフォルト起動モード（DB設定優先）。 |
| **`PHRONEL_MAX_RESULTS`** | `10` | **インフラ設定**: X 検索・観測時に収集する最大ツイート取得件数（API消費制限・費用抑制用）。 |
| **`PHRONEL_GEMINI_API_KEY`** | `None` | **クレデンシャル**: Gemini API キー。（`gemini_api_key` キーと同等、環境変数優先） |
| **`PHRONEL_X_BEARER_TOKEN`** | `None` | **クレデンシャル**: X OAuth 2.0 Bearer Token。 |
| **`PHRONEL_X_API_KEY`** | `None` | **クレデンシャル**: X API Key (Consumer Key)。 |
| **`PHRONEL_X_API_SECRET`** | `None` | **クレデンシャル**: X API Secret (Consumer Secret)。 |
| **`PHRONEL_X_ACCESS_TOKEN`** | `None` | **クレデンシャル**: X Access Token。 |
| **`PHRONEL_X_ACCESS_TOKEN_SECRET`** | `None` | **クレデンシャル**: X Access Token Secret。 |

---

## 5. AIペルソナ専用テーブル (`AgentPersona`) [新規追加!]

AIのキャラクター、口調（トーン）、名前、営業戦略方針などは、アプリケーションの技術設定とは明確に分離された独立したデータベーステーブル **`AgentPersona`** で管理されます。
TUIの「Persona Settings」タブから視覚的にCRUD（追加・編集・削除・有効化）操作を行うことができ、複数のペルソナ（Ken、Phronelなど）を切り替えて運用することが可能です。

### テーブル構造とフィールド一覧

| カラム名 | データ型 | デフォルト設定値 | 役割と説明（プロンプトインジェクションマッピング） |
| :--- | :--- | :--- | :--- |
| **`id`** | `INTEGER` (主キー) | 自動採番 | レコード識別用ID。 |
| **`name`** | `VARCHAR` | `"Phronel"` | AIの**名前**。自己紹介や戦略定義時に `Identity: You are '{name}'` としてインジェクションされます。 |
| **`role`** | `VARCHAR` | `"SNS Sales Representative..."` | AIの**専門分野・役職**。`role: '{role}'` としてAIの視点定義にブレンドマッピングされます。 |
| **`tone`** | `VARCHAR` | `"Professional, helpful, ..."` | AIの**キャラクター・話し方・トーン**。DSPyの `style` パラメータに入力され、絵文字数や専門性を統御します。 |
| **`constraints`** | `VARCHAR` | `"Max 280 chars. ..."` | 送信時の**制約・足切りルール**。DSPyの `constraints` パラメータに入力され、無駄な生JSONの出力などを強力に防止します。 |
| **`sales_strategy`** | `VARCHAR` | `"Focus on providing value..."` | AIがSNS営業で満たすべき**ビジネス戦略・行動規範**。DSPyの `strategy` パラメータへリアルタイム流し込みされます。 |
| **`observe_keyword`** | `VARCHAR` | `None` | ペルソナ固有の監視検索キーワード（カンマ区切りで `生成AI, AIエージェント` のように複数指定可能）。 |
| **`is_active`** | `BOOLEAN` | `True` / `False` | **有効化フラグ**。アクティブにされたペルソナが `get_active_persona()` でJITで読み込まれ、AIエージェントの現在の人格に即時適用されます。 |

---

## 6. ペルソナ & ナレッジ連関表 (`PersonaSourceLink`) [新規追加!]

複数のペルソナ間でナレッジベース（ファイル/URL）を自在に分離、または共有する多対多（N:N）の関係をデータベース上で動的に永続化・結合するための中間テーブルです。

### テーブル構造とフィールド一覧

| カラム名 | データ型 | デフォルト設定値 | 役割と説明 |
| :--- | :--- | :--- | :--- |
| **`persona_id`** | `INTEGER` (主キー, 外部キー) | なし | 関連付け対象のペルソナID（`AgentPersona.id`への参照）。 |
| **`source`** | `VARCHAR` (主キー) | なし | 関連付け対象のドキュメントソース名（ファイルパスやURL文字列）。 |

推論実行時、ChromaDBの検索パラメータ `where` に対して、本テーブルに格納されている該当ペルソナの許可ソース一覧が **`{"source": {"$in": linked_sources}}`** 演算子として動的にインジェクションされ、別ペルソナのドメイン知識との相互混入（ハルシネーション）を論理的に100%防止します。

---
