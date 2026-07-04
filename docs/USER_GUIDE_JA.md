# Phronel AI Agent - User Guide

このガイドでは、Phronel AI Agent（ソフィア）の基本的なセットアップと運用方法について解説します。

## 1. インストールと初期設定

Python 3.10以上がインストールされた環境で実行してください。

```bash
# 仮想環境の作成とアクティベート (推奨)
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate   # Windows

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 初期設定ウィザード

システムを最初に利用する前に、APIキーの登録を行います。

```bash
python -m phronel_ai_agent init
```
ターミナル上でプロンプトが表示されるので、以下の情報を順に入力してください。
1. **X (Twitter) API Keys**: X Developer Portal から取得したキー群
2. **Gemini API Key**: AIの「脳」として利用するGoogle GeminiのAPIキー
3. **Execution Mode**: 実行モード（最初は `manual` や `dry-run` を推奨します）

## 2. 実行モードの切り替え
エージェントは指定されたキーワードを監視し、自動で情報収集・投稿案の作成を行います。
設定コマンドで実行モードを変更することで、自律性のレベルをコントロールできます。

```bash
# 安全なシミュレーションモード（投稿は行われない）
python -m phronel_ai_agent config execution_mode dry-run

# 半自動モード（5分ごとに提案を作成するが、実行には手動承認が必要）
python -m phronel_ai_agent config execution_mode semi-auto

# 全自動モード（提案から投稿まで完全自動で5分ごとに実行）
python -m phronel_ai_agent config execution_mode auto

# 監視するキーワードの変更
python -m phronel_ai_agent config observe_keyword "生成AI"
```

詳細な設定パラメータについては [CONFIG_REFERENCE.md](./CONFIG_REFERENCE.md) をご参照ください。

## 3. TUI (Textual User Interface) ダッシュボード

エージェントの常駐監視と手動でのアクション承認を行うためのダッシュボード（TUI）を起動します。

```bash
python -m phronel_ai_agent start
```

### ダッシュボードの機能
TUIは**4つのタブ**で構成されています（マウスクリック、または矢印キーによるリスト移動で直感的に切り替え可能）。

*   **Dashboard タブ**:
    *   **ログビュー**: エージェントの検索、AIの分析結果、エラーなどのログがリアルタイムに流れます。
    *   **ステータスパネル**: 現在のモードと、承認待ち（Pending）のアクション数が表示されます。
    *   **手動ボタン**: `Run Observe` (指定キーワードで情報収集・提案作成) や `Run Propose` (特定の話題で提案作成) を手動でトリガーできます。
*   **Action Review Tab**:
    *   AIが作成した「投稿案（Action）」がリストで表示されます。
    *   `Approve Selected`: 選択した提案を「承認」状態にします。
    *   `Execute Selected`: 承認された提案を、実際にXへ投稿（Execute）します。
    *   `Reject Selected`: 不適切な提案を却下します。
    *   **行のダブルクリック / Enterキー**: アクションの**「詳細モーダル（Action Detail Modal）」**がポップアップ表示されます。もしアクションが `reply` または `like` であれば、**裏側の非同期バックグラウンド処理により自動的に会話スレッド全体の過去ログ（最大10往復）をX APIから動的に取得・時系列パース**し、色付けされた対話ログとしてモーダル上に表示します。これにより、前後の会話の流れを完璧に把握した上で安心して承認を行えます。
*   **Knowledge Base Tab**:
    *   エージェントが現在学習している知識ソースの一覧表が左カラムに表示されます。一覧表には **`Linked`** 列があり、現在アクティブなペルソナに紐付け参照が許可されているソースに **`[ ✔ ] Yes`** マークが表示されます。
    *   左側の行を選択（シングルクリック/キーボード上下）すると、対応するファイルやURLの生のテキストチャンクが右側の**「Source Content Preview」**に即座にスクロールプレビューされます（JITインタラクション）。
    *   **`[ + Learn Material (File/URL) ]` ボタン**: クリックすると**画面中央に「Import Knowledge Material」モーダルウインドウ**がポップアップ表示されます。ここにローカルファイルの絶対/相対パス、またはWeb上のURLを入力するだけで自動判別（Auto-detect）して取り込み学習を行います。
    *   **`[ Link/Unlink Active Persona ]` ボタン (新規追加!)**: 選択しているドキュメント知識（ソース）を、現在アクティブなペルソナに対して一発で紐付け / 紐付け解除（トグル）します。
    *   **`[ Delete Selected ]` ボタン**: 選択されているナレッジソース（および関連する全ベクトル/テキストチャンク）を、ChromaDBとSQLiteデータベースから同期して完全に削除し、ハルシネーションを能動的に防ぎます。
*   **Persona Settings Tab**:
    *   エージェントの「名前」「役割」「口調・トーン」「送信制約」「営業戦略ガイドライン」を設定・一元管理します（ナレッジ同様の Master-Detail レイアウト）。
    *   **左カラム (Registered Personas 一覧)**: 登録されているすべてのペルソナ（ID、名前、および有効化ステータス「★ Active」）を表示。
    *   **右カラム (Edit Selected Persona 編集フォーム)**:
        *   `Agent Name (名前)`: エージェント名（例: Phronel）
        *   `Professional Role (役割・専門性)`: ポジションや設定（例: AI SaaS Sales Representative...）
        *   `Tone of Voice (口調・トーン)`: キャラクターやキャラクター口調を設定
        *   `Constraints (送信制約・足切りルール)`: 文字数制限や出力制約を指定
        *   `Sales Strategy Guideline (営業戦略・行動規範)`: 満たすべきセールス目標・ポリシーを記述
        *   `Search Keywords (検索キーワード - カンマ区切り)` (新規追加!): このペルソナが自律巡回して営業活動を行うための固有のキーワードを設定します。**カンマ区切りで複数のキーワードを指定可能**（例: `AI エージェント, 生成AI, LLM`）で、自律運行時にすべてのキーワードをループ監視します。
    *   **操作ボタン群**:
        *   `[ Save Changes ]`: 編集中のペルソナの変更内容をSQLiteに保存（更新）。
        *   `[ Add New Persona ]`: 新しいペルソナテンプレートを新規追加して編集開始。
        *   `[ Activate Selected ]`: 選択したペルソナを本番稼働用に即時有効化。有効化した瞬間から、AIが生成するテキストのキャラクターが切り替わります。
        *   `[ Delete Selected ]`: 不要になったペルソナを安全に削除（現在稼働中のアクティブペルソナは、不意のシステムエラーを防ぐため削除できない安心ガード設計）。

### タブ画面遷移時のJIT自動更新 (UX最適化)
ダッシュボード上のいずれかのタブ（Dashboard、Action Review、Knowledge Base、Persona Settings）を切り替えたその瞬間に、**裏側のバックグラウンド処理により全画面の表示データが自動的にデータベースの最新状態へJIT（即時）で一斉同期リフレッシュ**されます。これにより、手動のRefreshボタンを一切押すことなく、常に最新の紐付けチェックマークやステータスが綺麗に連動表示されます。

### ショートカットキー
- `s`: エージェントのサイクル（情報収集・提案）を1回手動で回します。
- `r`: データを最新状態に更新します（Refresh）。
- `q`: ダッシュボードを終了します。

## 4. 知識（RAG）の取り込み

エージェントが投稿を作成する際、自社製品や特定のドメイン知識を参考にするためのコマンドです。MarkdownやTextファイルのインポートに加え、Web URLからのインテリジェントHTMLパース学習、および取り込んだ知識の一覧・削除が可能です。

### ① ローカルファイルからの学習
```bash
python -m phronel_ai_agent learn ./docs/my_product_info.md
```
取り込まれたテキストは自動分割（チャンク化）され、ChromaDB（ベクトルストア）およびSQLiteデータベースに同時に保存され、AIが文脈に合ったツイートを生成する際に自動で参照されます。

### ② Web上のURLからの自動HTML学習
```bash
python -m phronel_ai_agent learn-url "https://example.com/product-specification"
```
対象URLから自動的にHTMLをダウンロードし、スクリプトやスタイルなどを綺麗に除去して「本文テキスト」のみをインテリジェントに抽出。分割チャンク化してナレッジベースに取り込みます。

### ③ インポート済みソースの一覧表示
```bash
python -m phronel_ai_agent learn-list
```
現在エージェントが取り込み学習を完了しているすべてのソース（ファイルやURLの一覧、分割されたチャンクの総数、学習日時）を美しい Rich テーブル形式で一覧表示します。

### ④ インポート済みソースの個別削除
```bash
python -m phronel_ai_agent learn-remove "./docs/my_product_info.md"
```
指定された特定のドメイン知識ソース（および関連するすべてのベクトルデータとDB行）を一発で同期削除し、古い情報に基づくAIのハルシネーションを完璧にコントロールします。

