# Phronel AI Agent

Phronelは、自律的に情報収集から投稿案の作成・X(Twitter)への投稿までを一貫して行う「SNS営業担当」AIエージェントです。
単純な定型文のボットではなく、DSPy（LLMプロンプトの最適化フレームワーク）を利用し、環境（タイムライン）を **「観察」** し、どのように振る舞うべきか **「戦略」** を立て、文脈に合った質の高い投稿を **「生成」** する高度な自律性を持っています。

## 主な特徴

- 🧠 **思考するエージェント (DSPy)**: LLM（Google Geminiなど）を用いてタイムラインのトレンドや感情を分析し、最適なアクション（投稿・いいね・リプライ・静観）を実在のツイートIDと連携させて自ら判断します。
- 👥 **マルチペルソナ管理 (SQLModel / 新機能!)**: 専用の `AgentPersona` テーブルを新設。TUI画面から名前、役割、口調（トーン）、送信制約、営業戦略方針の異なる複数の人格を自在に登録・編集・削除・ワンクリックでアクティブ化できます。
- 📊 **RAGナレッジベース (ChromaDB + Web取り込み / 新機能!)**: ローカルファイル（Markdown/Text）の学習に加え、任意のWebサイトのURLを入力するだけでインテリジェントにHTMLの不要タグ（スクリプト、スタイル、メタ情報）を除去して「本文テキスト」のみを抽出学習するクローラー機能を内蔵。
- 🖥️ **リッチなターミナルUI (TUI / パッケージ分割化!)**: Textualを利用したグラフィカルなCUIダッシュボードを搭載（`tui/` パッケージへとモジュール分割完了）。
  - **Dashboard タブ**: AIの思考ログ・動作状況のリアルタイム監視。
  - **Action Review タブ**: AIが作成した「本物のツイートIDに紐づくリプライ・いいね・投稿」のレビュー、承認（Approve）、送信実行（Execute）。
  - **Knowledge Base タブ**: 現在学習済みの全ナレッジ一覧、テキストチャンクの動的スクロールプレビュー、個別完全消去、および中央にポップアップする「追加学習モーダル」。
  - **Persona Settings タブ**: 複数ペルソナの動的な新規追加、編集、削除、即時アクティブ化切り替え。
- ⚙️ **柔軟な実行モード & 環境変数オーバーライド**:
  - `.env` によるDBパス・ChromaDB保存先・使用するGeminiモデル・最適化プロンプト保存先の一括設定と、セキュリティ保護（`.env` を `.gitignore` に自動追加）。
  - ユーザーがTUIで設定変更した「実行時に動的に変更させたい設定（運用モードや検索キーワード）」はSQLiteを最優先し、未設定時は環境変数へフォールバックするハイブリッド設計。
  - 運用モード：`manual` (手動操作), `semi-auto` (自動提案・手動承認), `auto` (全自動自律投稿), `dry-run` (APIを消費しない疑似実行)

## クイックスタート

Python 3.10 以上が必要です。

### 1. インストール
```bash
git clone <repository_url>
cd sns_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境設定（.env）
`.env.example` を `.env` にコピーし、APIキーやパスなどを設定します。（本番用APIキーがなくても、自動でセキュアな Mock モードが立ち上がるため安全に開発・テストが可能です）
```bash
cp .env.example .env
```

### 3. 初期設定（APIキーの登録）
```bash
python -m phronel_ai_agent init
```
*※X Developer Portalから取得したAPI Keyと、Google Gemini API Keyを対話式にデータベースへ登録することもできます。*

### 4. TUI ダッシュボードの起動
```bash
python -m phronel_ai_agent start
```

## ドキュメント

より詳細な使い方や設定方法については、以下のドキュメントをご参照ください。

- [User Guide (ユーザーガイド)](./docs/USER_GUIDE.md) : 新設された4つのTUIタブの使い方、モーダルによるファイル/URL追加、新CLIコマンド等
- [Configuration Reference (設定リファレンス)](./docs/CONFIG_REFERENCE.md) : ハイブリッド環境変数キーの一覧、新ペルソナテーブルの構造、各実行モードの詳細等
- [Architecture (システムアーキテクチャー / コードマップ)](./docs/ARCHITECTURE.md) : 本アプリケーションのシステムアーキテクチャ、およびコードの説明資料

---
