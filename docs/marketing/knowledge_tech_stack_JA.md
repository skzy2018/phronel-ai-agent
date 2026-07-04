# Phronel AI Agent の技術スタックとモダン設計

Phronelは、単に実用的なだけでなく、開発者がコードを見て触るだけでワクワクするような、最先端のAI・Pythonエコシステムを用いて美しく設計されています。

---

## 1. テクノロジースタック

### 🧠 AI / LLM オーケストレーション: DSPy Framework
従来のテンプレート（F-string）による「静的プロンプト」を完全に廃止。プログラマブルにLLMを制御する **DSPy** を採用しています。
*   **Signatures / Modules**: `AnalyzeTrend`、`GenerateTweet`、`GenerateReply` などの役割ごとにインターフェース（Signature）を定義。自律思考を行う `Strategist` やコンテンツ生成を行う `Creator` などの堅牢なモジュール設計。
*   **Optimizers**: 過去の実績データから、最適なFew-Shot事例をインテリジェントに逆引き構築し、プロンプトを動的に学習・最適化する自己進化ループの基礎。

### 🖥️ ユーザーインターフェース: Textual (TUI)
ターミナル上でリッチなGUIライクな操作性を提供する **Textual** フレームワークを採用。
*   常駐監視中のバックグラウンドタスクと同期する「リアルタイムログ」と、JIT（オンデマンド）でのデータの自動リフレッシュ。
*   4つの洗練されたタブ構成：
    1.  **Dashboard**: 常駐動作状況のモニタリングと手動トリガー。
    2.  **Action Review**: 生成されたPendingアクションの承認（Approve）/ 却下（Reject）/ 実行（Execute）の直感操作。
    3.  **Knowledge Base**: ベクトル化されたナレッジソースの確認、個別削除、およびURL/ファイルを即座に取り込むインタラクティブモーダル。
    4.  **Persona Settings**: 複数ペルソナ（ID、名前、役割、口調、目標、制約ルール）の動的追加・編集・即時切り替え。

### 📊 データ永続化 & ローカルRAG
*   **SQLite + SQLModel (SQLAlchemy)**: アカウント設定、アクション履歴、戦略思考ログ、マルチペルソナデータを一元管理。テーブル間の厳密なリレーション（ActionLog ➔ StrategyLog 外部キーバインド）により、意思決定とアクションの因果関係を完全保存。
*   **ChromaDB**: 完全にローカルで動作するオープンソースのベクトルデータベース。取り込まれたMarkdownファイルやスクレイピングされたWebサイトのテキストをチャンク分割して保存。オンプレミスで高度な意味的（セマンティック）検索を実現。

---

## 2. アーキテクチャの強み（開発者向け）

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

### JIT (Just-In-Time) 遅延初期化
アプリケーション起動時やモジュールインポート時の不要なファイルアクセス、DB読み出し、および環境変数未登録による警告を100%防ぐため、ChromaDB接続やLLM設定、 optimized prompts のディスクロードは、**実際の推論やAPI要求が発生した最初のタイミングまで遅延ロード（Lazy Initialization）**されます。テストコードの収集時や、初期セットアップウィザード実行時も完全にクリーンで例外フリーな挙動を保証します。
