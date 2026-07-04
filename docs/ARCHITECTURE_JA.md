# Phronel AI Agent - System Architecture & Code Map

本ドキュメントは、「SNS営業窓口 AIエージェント」である **Phronel (ソフィア)** のシステム構成、データモデル、主要関数、および各機能との関連性を体系的に説明するための開発者ガイドです。

---

## 1. ディレクトリ構成 (Directory Structure)

本プロジェクトは、責務ごとに明確に分離されたレイヤー化アーキテクチャ（4層構造）を採用しています。これにより、各モジュールが疎結合になり、テストや将来の拡張が容易になっています。

```text
sns_agent/
├── .gitignore                   # 環境設定（.env）等のGit除外
├── .env.example                 # 環境変数設定のテンプレート
├── .env                         # ローカルの秘密APIキーや基本パスの設定
├── README.md                    # プロジェクト全体の導入ガイド
├── requirements.txt             # 依存ライブラリの定義
├── docs/                        # エンドユーザー/管理者向け各種マニュアル
│   ├── USER_GUIDE.md            # 初期設定・使用方法
│   ├── ARCHITECTURE.md          # [本書] システムアーキテクチャー / コードマップ
│   └── CONFIG_REFERENCE.md      # 各種パラメータの解説
├── tests/                       # 各種ユニットテスト
│   ├── conftest.py              # テスト環境の完全クリーン隔離機構
│   ├── test_db.py               # データベース操作のテスト
│   ├── test_metrics.py          # 評価メトリクスのテスト
│   ├── test_observer.py         # 観察ロジックのテスト
│   └── test_phase1~4.py         # フェーズごとの結合・機能テスト
└── phronel_ai_agent/             # アプリケーションソースコード
    ├── __init__.py              # パッケージ初期化
    ├── __main__.py              # コマンドライン実行エントリーポイント
    ├── core/                    # [Core層] データベース定義、設定、定数管理
    │   ├── db.py                # SQLite接続とDB/リポジトリ関数
    │   ├── config.py            # アプリケーション設定管理 (ConfigManager)
    │   └── models.py            # SQLModelによるデータモデル定義
    ├── interfaces/              # [Presentation層] ユーザーインターフェース (CLI/TUI)
    │   ├── main.py              # CLI (Typer) コマンドの定義
    │   └── tui/                 # [TUIパッケージ / モジュール分割完了!]
    │       ├── __init__.py      # パッケージエントリーポイント
    │       ├── app.py           # メインApp (PhronelApp) & リアルタイムログ
    │       ├── modals.py        # 各モーダル画面 (Action詳細, 知識追加モーダル)
    │       ├── dashboard_view.py# ステータス要約ビュー
    │       ├── review_view.py   # 投稿承認フロービュー
    │       ├── knowledge_view.py# RAGドメイン知識管理ビュー (プレビュー＆削除)
    │       └── persona_view.py  # マルチペルソナ設定管理ビュー
    ├── services/                # [Infrastructure層] 外部サービス、DBクライアント
    │   ├── x_client.py          # X API (Tweepy) クライアント (Online/Mock対応)
    │   └── knowledge.py         # ChromaDBベクトルストア連携 (RAGナレッジ / URLインテリジェントパーサー)
    └── skills/                  # [Domain/Skill層] 自律AIロジック
        ├── brain.py             # 思考コア (DSPy Strategist & Creator / 動的ペルソナ結合)
        ├── observer.py          # 情報収集 (特定キーワード・トレンド監視 / 実ツイートID伝播)
        ├── executor.py          # アクション実行 (投稿、リプライ、いいね、ドライラン対応)
        ├── analyst.py           # 分析・最適化 (日次レポーティング / DB動的Example逆引きFew-Shot)
        └── metrics.py           # [評価層 / 新規追加!] 多層スコアリング・コサイン類似度メトリクス
```

---

## 2. データモデル定義 (Data Models)

データモデルは `phronel_ai_agent/core/models.py` で `SQLModel` を用いて定義されており、ローカルの SQLite データベース (`phronel_agent.db`) に保存されます。

### 2.1. AgentConfig
エージェントの各種設定（APIキー、実行モード、ターゲットキーワードなど）をKey-Value形式で永続化します。
*   **`key` (str, 主キー)**: 設定項目名 (例: `gemini_api_key`, `execution_mode`)
*   **`value` (str)**: 設定値
*   **`description` (Optional[str])**: 設定項目の説明
*   **`updated_at` (datetime)**: 最終更新日時 (デフォルト: UTC現在時刻)

### 2.2. KnowledgeChunk
RAG (Retrieval-Augmented Generation) に用いるドキュメントやWebURL素材を、チャンク（分割テキスト）単位でSQLite側に参照用として保存します。
*   **`id` (Optional[int], 主キー)**: 自動採番
*   **`content` (str)**: 分割されたテキスト本文
*   **`source` (str)**: 元ファイルのパスまたはソースURL
*   **`embedding_id` (Optional[str])**: ベクトルデータベース (ChromaDB) 内の対応ベクトルID
*   **`created_at` (datetime)**: 取り込み日時

### 2.3. ActionLog
AIが提案した、または人間が承認して実行したすべてのSNS上のアクション（つぶやき、返信、いいね等）のステータスと履歴を追跡します。
*   **`id` (Optional[int], 主キー)**: 自動採番
*   **`action_type` (str)**: `'tweet'`, `'reply'`, `'like'`, `'follow'` のいずれか
*   **`content` (Optional[str])**: 投稿・リプライの本文
*   **`target_id` (Optional[str])**: 反応対象のツイートIDまたはユーザーID
*   **`status` (str)**: ステータス (`pending`, `approved`, `executed`, `failed`)
*   **`result_json` (Optional[str])**: 実行完了時にX APIから返却されたレスポンスのJSON文字列
*   **`strategy_log_id` (Optional[int], 外部キー)**: 本アクションを意思決定させた戦略思考ログ `StrategyLog` の主キーID（1対1リレーション）
*   **`created_at` (datetime)**: 提案生成日時
*   **`executed_at` (Optional[datetime])**: アクションの実行完了日時

### 2.4. StrategyLog
AIが状況を観察し、どのような分析に基づいて上記アクションを決定したかという「思考・戦略プロセス」を記録し、インサイト報告のソースとします。
*   **`id` (Optional[int], 主キー)**: 自動採番
*   **`context_summary` (str)**: 状況の要約 (例: "Timeline analysis")
*   **`strategy_text` (str)**: AIが考えた戦略・判断の根拠 (CoT出力)
*   **`model_name` (str)**: 推論に使用したLLMモデル名 (例: `gemini-2.5-flash`)
*   **`created_at` (datetime)**: ログ作成日時

### 2.5. AgentPersona
LLMによって実行するときのペルソナ情報と営業指針を格納するテーブルです。複数登録でき、activeな情報で実行されます。
*   **`id` (Optional[int], 主キー)**: 自動採番
*   **`name` (str)**: ペルソナの名前 / デフォルト: "Phronel"
*   **`role` (str)**: ペルソナの役割・専門性 / デフォルト: "SNS Sales Representative..."
*   **`tone` (str)**: ペルソナの口調・トーン / デフォルト: "Professional, polite, helpful..."
*   **`constraints` (str)**: 信時の絶対禁止ルール / デフォルト: "Max 280 chars..."
*   **`sales_strategy` (str)**: 営業戦略方針 / デフォルト: "Focus on providing value and solving pain points..."
*   **`is_active` (bool)**: アクティブかどうか (データのどれか一つがtrue)

---

## 3. 関数・クラスマップ (Function & Method Map)

各レイヤーに含まれるクラスおよび関数のシグネチャ、動作概要を網羅した詳細マップです。

| レイヤー | モジュール・ファイル | クラス/関数 | 引数と戻り値 | 動作内容の説明 |
| :--- | :--- | :--- | :--- | :--- |
| **Core** | `core/db.py` | `init_db` | `()` -> `None` | SQLite DBのテーブルを初期化（SQLModelベース） |
| | | `get_session` | `()` -> `Session` | 新しいデータベースセッションを生成して返却 |
| | | `get_actions_by_status` | `(statuses: List[str])` -> `List[ActionLog]` | 指定されたステータスに一致するアクション一覧を逆順で取得 |
| | | `get_pending_action_count` | `()` -> `int` | `pending` (保留中) 状態のアクション総数をカウントして返却 |
| | | `update_action_status` | `(action_id: int, new_status: str)` -> `Optional[ActionLog]` | 指定IDのアクションステータスを更新・永続化する |
| | | `get_active_persona` | `()` -> `AgentPersona` | 現在アクティブなペルソナ情報を取得。未設定時はデフォルトをJIT自動生成。 |
| | | `save_active_persona` | `(name, role, tone, constraints, strategy)` -> `AgentPersona` | アクティブペルソナ情報を一括保存・作成する。 |
| | | `list_personas` | `()` -> `List[AgentPersona]` | 登録されているすべてのペルソナ情報を取得。 |
| | | `add_persona` | `(name, role, tone, constraints, strategy)` -> `AgentPersona` | 新しいペルソナレコードを追加。 |
| | | `update_persona` | `(id, name, role, tone, constraints, strategy)` -> `AgentPersona` | 指定IDのペルソナ情報を更新。 |
| | | `delete_persona` | `(id)` -> `bool` | 指定IDのペルソナを消去（アクティブ行はエラーガードで削除不可）。 |
| | | `activate_persona` | `(id)` -> `bool` | 指定IDのペルソナをアクティブ化し、他をすべて非アクティブ化。 |
| | `core/config.py` | `ConfigManager.get` | `(key: str, default: Optional[str])` -> `Optional[str]` | 指定された設定値をDBから取得。環境変数 `PHRONEL_<KEY>` をフォールバックとして優先順位判定を行う。 |
| | | `ConfigManager.set` | `(key: str, value: str, description: Optional[str])` -> `AgentConfig` | 指定のキー設定値をDBに保存・更新する |
| **Services** | `services/knowledge.py` | `KnowledgeBase.__init__` | `(persist_directory: Optional[str])` | ChromaDBのクライアントおよびスプリッターを遅延初期化（オンデマンド結合）用に準備。 |
| | | `KnowledgeBase.add_document`| `(content: str, source: str)` -> `int` | テキストをチャンク分割し、ChromaDBとSQLite（KnowledgeChunk）の両方に保存 |
| | | `KnowledgeBase.add_url` | `(url: str)` -> `int` | 指定されたWeb URLからHTMLを自動取得し、不要タグを除去してプレーンテキストとして学習・保存。 |
| | | `KnowledgeBase.list_sources`| `()` -> `List[Dict[str, Any]]` | 取り込み済みのナレッジソース、チャンク総数、取り込み時間をSQLiteからクエリ。 |
| | | `KnowledgeBase.get_chunks_by_source`| `(source: str)` -> `List[KnowledgeChunk]` | 特定のソースに紐づく実際の全テキストチャンクを取得。 |
| | | `KnowledgeBase.delete_source`| `(source: str)` -> `int` | 指定されたソースおよび関連する全ベクトル・テキストチャンクをChromaDBとSQLiteから同期完全削除。 |
| | | `KnowledgeBase.query` | `(query_text: str, n_results: int)` -> `List[str]` | クエリ文に類似するチャンクをChromaDBからRAGコンテキストとして取得 |
| | `services/x_client.py` | `XClient.__init__` | `()` | 認証用内部変数 and 認証フラグの初期化 |
| | | `XClient._authenticate` | `()` -> `None` | `ConfigManager` から認証情報を取得し Tweepy API (V2 & V1.1) を初期化。情報が足りない場合はMockモードで動作 |
| | | `XClient.post_tweet` | `(text: str)` -> `Optional[dict]` | X APIでツイートを投稿する（Mock時は標準出力） |
| | | `XClient.like_tweet` | `(tweet_id: str)` -> `Optional[dict]` | 指定されたツイートを「いいね」する |
| | | `XClient.reply_to_tweet` | `(tweet_id: str, text: str)` -> `Optional[dict]` | 指定されたツイートに対してリプライを投稿する |
| | | `XClient.search_tweets` | `(query: str, max_results: int)` -> `Any` | 関連キーワードで最新のツイート群を検索・取得 |
| | | `XClient.get_tweet_metrics`| `(tweet_ids: List[str])` -> `List[dict]` | 投稿済みツイート群の「いいね数」「リツイート数」などの統計データを一括取得 |
| **Skills** | `skills/brain.py` | `Strategist.analyze_timeline`| `(tweets: List[str])` -> `Optional[dict]` | 収集したツイート群をDSPy CoT (`AnalyzeTrend` Signature) で分析し戦略を策定 |
| | | `Creator._get_knowledge` | `(topic: str)` -> `str` | トピックに関連するチャンクを知識ベースから引き出し、1つのRAG用文脈テキストにまとめる |
| | | `Creator.create_tweet` | `(strategy_insight: str, topic: str)` -> `str` | DBから動的取得したアクティブな名前・役割・トーン・制約・営業指針をインジェクションして、投稿用つぶやきを生成。 |
| | | `Creator.create_reply` | `(target_tweet: str, strategy_insight: str, topic: str)` -> `str` | 対象ツイートに対するリプライ文を、DBから動的取得したペルソナ情報を注入して生成。 |
| | | `Brain.__init__` | `()` | メンバー変数を初期化。LLM構成や Few-Shot プロンプトファイルのロード処理は遅延（オンデマンド）で実行。 |
| | | `Brain._ensure_ready` | `()` -> `None` | 初めて推論やAPIが呼ばれたタイミング（JIT）で、Gemini LLM 構成と Few-Shot プロンプトのディスク読込を実行。 |
| | | `Brain.process_and_propose`| `(source_data: list, context_summary: str)` -> `Optional[ActionLog]` | 観察データ（辞書オブジェクト/文字列）から、分析 ➔ 動的ペルソナ流し込み生成 ➔ アクション提案。StrategyLogとActionLogを外部キーで強固に紐付けて保存。 |
| | | `Brain.create_tweet_proposal`| `(topic: str)` -> `ActionLog` | 特定のトピックをベースに、RAGを用いて新しい投稿案を作成し、`pending` 状態で保存 |
| | `skills/observer.py` | `Observer.observe_keyword`| `(keyword: str, max_results: int)` -> `Optional[ActionLog]` | Xを特定キーワードで検索、取得した実ツイート情報（ID、ユーザーID等）をメタデータとして保持したまま `Brain.process_and_propose` に流して自律的アクションを提案する |
| | `skills/executor.py` | `execute_action` | `(action_id: int)` -> `Optional[ActionLog]` | 指定されたアクションを実行。`execution_mode` が `dry-run` ならAPIを叩かず擬似ログを出力。成功/失敗のログを保存 |
| | | `approve_action` | `(action_id: int)` -> `Optional[ActionLog]` | 指定のアクションを `pending` から `approved` (承認済み) に変更 |
| | `skills/analyst.py` | `Analyst.generate_daily_report`| `(target_date: Optional[datetime])` -> `str` | その日に実行されたアクション、策定された戦略、Xから取得したインサイト統計情報を集計し、DSPyで日次報告書を生成 |
| | | `Analyst.optimize_creator_prompts`| `()` -> `bool` | SQLite の ActionLog/StrategyLog の実績リレーション行から実際の成功事例（Example）を動的マイニング抽出して、DSPy `BootstrapFewShot` を用いて最適 Few-Shot プロンプトを作成・保存。 |
| | `skills/metrics.py` | `phronel_multi_tier_metric`| `(example, pred, trace)` -> `float` | **[評価層]** ハードガードレール（文字数280、空文字、ハルシネーション検出）、美的・運用制約（ハッシュタグ数、絵文字数）、およびChromaDBの埋め込みを用いた戦略文章とのコサイン類似度セマンティクス評価から、0.0〜1.0 の高度な多層スコアを算出。 |
| **Interfaces**| `interfaces/main.py` | 各 CLI コマンド | - | `phronel start / init / config / learn / learn-list / learn-remove / learn-url / propose / observe / actions / approve / execute / report / optimize` をTyperで提供 |
| | `interfaces/tui/app.py` | `PhronelApp.compose` | `()` -> `ComposeResult` | Header、Footer、4つのタブ表示コンテナ（Dashboard, Action Review, Knowledge Base, Persona Settings）を統合構築。 |
| | | `PhronelApp.on_mount` | `()` -> `None` | `TuiLogHandler` ロギングを安全（クラッシュ防止）に接続し、5分間隔の定期ジョブ監視を開始。 |
| | | `PhronelApp.update_ui_status`| `()` -> `None` | 全画面およびマスタ・ディテールビュー（Action, Knowledge, Persona）をデータベースの最新状態へ同期（リフレッシュ）する。 |
| | `interfaces/tui/modals.py`| `ActionDetailModal.compose`| `()` -> `ComposeResult` | アクションの詳細文や実行メタデータをポップアップ表示。 |
| | | `KnowledgeImportModal.compose`| `()` -> `ComposeResult` | 画面中央にポップアップ表示され、ファイルパス/URLの自動判別（Auto-Detect）取り込みを仲介。 |
| | | `dashboard_view.py` | `AgentStatus.compose` | `()` -> `ComposeResult` | ダッシュボード上部の要約パネル `AgentStatus` のレイアウト構築と更新。 |
| | | `review_view.py` | `ActionReview.compose` | `()` -> `ComposeResult` | アクション承認テーブル（DataTable）と承認/却下/実行ボタンアクション。 |
| | | `knowledge_view.py` | `KnowledgeBaseView.compose`| `()` -> `ComposeResult` | 知識ソース一覧表（左）とテキストチャンクプレビュー（右：RowHighlighted連動）、モーダル呼び出しボタン。 |
| | | `persona_view.py` | `PersonaSettingsView.compose`| `()` -> `ComposeResult` | ペルソナ一覧（左）とペルソナ/戦略編集コンテナ（右）、保存/追加/削除/有効化アクション。 |

---

## 4. 各機能の関数の位置付け・ライフサイクル (Feature-Function Mapping)

Phronelの備える主要機能と、それを支える各関数の実行順序、協調関係をマッピングします。

### 4.1. 機能1：Xアカウントの連携設定と認証 (Credentials & Initialization)
初期化のステップであり、データベース設定テーブル（`AgentConfig`）を初期化し、認証を確立します。
1. `interfaces/main.py (init)` コマンド起動。または TUI 起動。
2. `core/db.py (init_db)` が実行され SQLite が構築される。
3. ユーザーが入力した各種APIキー等が `core/config.py (ConfigManager.set)` によって永続化される。
4. 実行時、`services/x_client.py (XClient._authenticate)` が呼び出され、`ConfigManager.get` を経由して認証キーを取得。
5. Tweepy クライアントがセットアップされる（キーが欠損している場合はMockモードへ自動切替）。

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

### 4.2. 機能2：知識取り込みと RAG 連携 (Knowledge Ingestion & RAG)
営業資料などのMarkdownやTextファイルを学習し、高精度の回答・投稿を可能にする機能です。
1. `interfaces/main.py (learn)` コマンドからソースファイルを入力。
2. `services/knowledge.py (KnowledgeBase.add_document)` が呼び出される。
3. `RecursiveCharacterTextSplitter` がファイルを意味のあるチャンクに分割。
4. `ChromaDB` (ベクトルDB) にテキストとソース情報を登録。
5. `core/db.py` のセッションを介して、SQLite内の `KnowledgeChunk` テーブルに同じ内容をメタデータ付きで保存。
6. 後続の投稿・リプライ生成時、`skills/brain.py (Creator._get_knowledge)` が `KnowledgeBase.query` を呼び出し、キーワードにマッチした高関連チャンクを取り出す。

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

### 4.3. 機能3：X上のトレンド観測・自律的営業活動提案 (Trend Observation & Proposal Pipeline)
定期的に情報を観測し、アクション候補をデータベースに格納する一連のパイプラインです。
1. 定期タイマー、あるいは `interfaces/main.py (observe)` の手動実行をトリガーにする。
2. `skills/observer.py (Observer.observe_keyword)` が起動し、`services/x_client.py (XClient.search_tweets)` を用いて関連ツイートを取得。
3. 取得したツイート群を `skills/brain.py (Brain.analyze_timeline)` に流す。
4. `Strategist` モジュールが DSPy で内容を分析、トレンドのトピック・感情・そしてアクション案（リプライや投稿）を決定する。
5. 意思決定の裏付けとして `StrategyLog` をSQLiteに保存。
6. `Creator` が RAG 知識を引き出して最適なつぶやき・リプライを作成。
7. 作成されたコンテンツとターゲットを `ActionLog` に `pending` 状態で登録し、ユーザーのレビュー（承認）を待つ。

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

### 4.4. 機能4：承認フローとアクション実行 (Approval Flow & Execution)
提案されたアクションのレビュー、および実際のXへの実行を行います。
1. `interfaces/main.py (actions)` で提案一覧を確認。またはTUIの「Action Review」画面を開く。
2. ユーザーが承認を決定した際、`skills/executor.py (approve_action)` が動き、ステータスが `approved` に更新される。
3. `skills/executor.py (execute_action)` が呼び出される。
4. `core/config.py (ConfigManager.get("execution_mode"))` が `dry-run` の場合、APIコールをスキップし、ダミーレスポンスを生成。
5. `manual / semi-auto / auto` の場合は、`services/x_client.py (XClient.post_tweet / reply_to_tweet / like_tweet)` を実行し、実際のSNSに配信。
6. 送信が成功した場合、`ActionLog` のステータスを `executed` に変更し、レスポンスデータを `result_json` として保存、`executed_at` にタイムスタンプを押す。

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

### 4.5. 機能5：分析報告とプロンプト自動最適化 (Reporting & Optimization Cycle)
システムの成果を可視化し、PDCA（改善活動）を自律的に推進するためのコア機能です。
*   **レポーティング (`phronel report` / TUI「Generate Report」ボタン)**:
    1. `skills/analyst.py (Analyst.generate_daily_report)` が実行される。
    2. SQLiteから当日の `ActionLog` (実行済みアクション) と `StrategyLog` を取得・集計。
    3. `services/x_client.py (XClient.get_tweet_metrics)` を叩き、実際の投稿のいいね数・インプレッション数を集計。
    4. 集計データ（戦略、エンゲージメント、行動サマリー）を DSPy `GenerateDailyReport` に渡し、美しく整形された Markdown のインサイトレポートを作成して表示。

*   **プロンプト最適化 (`phronel optimize` / TUI「Run Optimizer」ボタン)**:
    1. `skills/analyst.py (Analyst.optimize_creator_prompts)` が実行される。
    2. 過去のデータから、高エンゲージメントだったアクションとその時採用された戦略を「成功デモ」として準備。
    3. DSPyの `BootstrapFewShot` を使用して、Creatorモジュール（`GenerateTweet` 等の Signature）の Few-Shot 訓練を実行。
    4. 指標に最も適合した最適プロンプトを `phronel_ai_agent/core/optimized_creator.json` としてファイル保存。
    5. 次回Brainインスタンスが立ち上がる際、`Brain._load_optimized_prompts` が走り、このJSONファイルから最適化されたプロンプトを自動リロード。自律的にエージェントが「賢く」進化し続ける。

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

本ドキュメントは、Phronelの最新コードベースに基づいて作成されています。今後の機能拡張・リファクタリング時に参照し、システムの整合性を保つための基礎としてご活用ください。
