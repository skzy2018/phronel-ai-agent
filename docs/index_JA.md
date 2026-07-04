# 🧠 Phronel AI Agent

> **DSPyとローカルRAGを搭載した、自律思考型SNS営業担当AIエージェント**

Phronel（ソフィア）は、自律的にタイムラインを観察・分析し、最適な営業戦略を組み立ててX（Twitter）上で高品質な対話を行う、オープンソースの常駐型AIエージェントです。

[:octicons-arrow-right-24: 今すぐ始める](./USER_GUIDE_JA.md){ .md-button .md-button--primary }
[:octicons-mark-github-16: GitHubで見る](https://github.com/skzy2018/phronel-ai-agent){ .md-button }

---

## ✨ 主要機能

!!! info "🧠 DSPyによるプロンプト自己進化サイクル"
    手動のプロンプトエンジニアリングは不要です。過去の送信実績データから、AIが「最もコンバージョン率の高いプロンプト（Few-Shot）」を自動で選定・最適化し続けます。

!!! success "👥 マルチペルソナ一元管理"
    TUI（ターミナルUI）から、複数のペルソナ（口調、営業目標、制約ルール）を瞬時に作成・編集・有効化できます。

!!! security "🔒 100%ローカル＆高セキュリティ"
    機密情報、APIキー、顧客データ、対話ログはすべてあなたのローカルPC内（SQLite / ChromaDB）にのみ保存。SaaS型サービスと異なり、外部サーバーへの情報漏洩リスクは一切ありません。

---

## 🚀 クイックスタート

```bash
# 1. リポジトリをクローン
git clone https://github.com/skzy2018/phronel-ai-agent.git
cd phronel-ai-agent

# 2. 仮想環境の作成と起動
python -m venv .venv
source .venv/bin/activate

# 3. 依存パッケージのインストール
pip install -r requirements.txt

# 4. 初期設定
python -m phronel_ai_agent init

# 5. TUI ダッシュボードの起動
python -m phronel_ai_agent start
```
