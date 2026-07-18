import pytest
import logging
from unittest.mock import patch
from sqlmodel import Session, SQLModel, create_engine

from textual.widgets import DataTable, TabbedContent, RichLog
from phronel_ai_agent.interfaces.tui import PhronelApp
from phronel_ai_agent.core.models import ActionLog, AgentConfig
import phronel_ai_agent.core.db as db

# テスト用のインメモリデータベース
sqlite_url = "sqlite:///:memory:"
test_engine = create_engine(sqlite_url)

@pytest.fixture(autouse=True)
def setup_test_db():
    """テストごとにDBをモック化し、初期データを投入する"""
    original_engine = db.engine
    db.engine = test_engine
    SQLModel.metadata.create_all(test_engine)
    
    with Session(test_engine) as session:
        # モードをmanualに設定
        session.add(AgentConfig(key="execution_mode", value="manual"))
        # テスト用の保留中アクションを1件追加
        session.add(ActionLog(action_type="tweet", content="Test tweet pending", status="pending"))
        # テスト用の承認済みアクションを1件追加
        session.add(ActionLog(action_type="reply", content="Test reply approved", status="approved"))
        session.commit()

    yield
    
    SQLModel.metadata.drop_all(test_engine)
    db.engine = original_engine

@pytest.mark.asyncio
async def test_tui_initial_startup():
    """TUIが正常に起動し、初期状態が正しく表示されるかテスト"""
    app = PhronelApp()
    async with app.run_test() as pilot:
        # Logウィジェットが存在するか確認
        log_view = app.query_one("#log_view", RichLog)
        assert log_view is not None
        
        # 起動時の初期メッセージが表示されているか確認
        log_content = "".join([strip.text for strip in log_view.lines])
        assert "Phronel AI Agent TUI Started" in log_content

@pytest.mark.asyncio
async def test_tui_logging_integration():
    """phronelロガー経由の出力がTUIのLogウィジェットに反映されるかテスト"""
    app = PhronelApp()
    async with app.run_test() as pilot:
        logger = logging.getLogger("phronel")
        test_message = "Integration test log message."
        
        # ロガーからメッセージを出力
        logger.info(test_message)
        
        # ログがUIに反映されるまで少し待機
        await pilot.pause()
        
        log_view = app.query_one("#log_view", RichLog)
        log_content = "".join([strip.text for strip in log_view.lines])
        assert test_message in log_content

@pytest.mark.asyncio
async def test_tui_action_review_tab():
    """Action ReviewタブのDataTableにデータが正しくロードされるかテスト"""
    app = PhronelApp()
    async with app.run_test() as pilot:
        # Action Reviewタブに切り替え
        tabbed_content = app.query_one(TabbedContent)
        tabbed_content.active = "tab_review"
        await pilot.pause()
        
        # DataTableを取得
        table = app.query_one("#action_table", DataTable)
        assert table is not None
        
        # 保留中と承認済みの2件がロードされているはず
        assert len(table.rows) == 2
        
        # テーブルの内容を検証
        rows_data = [table.get_row(row_key) for row_key in table.rows.keys()]
        contents = [row[2] for row in rows_data]
        statuses = [row[3] for row in rows_data]
        
        assert any("Test tweet pending" in c for c in contents)
        assert any("Test reply approved" in c for c in contents)
        assert "pending" in statuses
        assert "approved" in statuses

@pytest.mark.asyncio
async def test_tui_update_status():
    """UIのステータス更新が機能しているかテスト"""
    app = PhronelApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # 初期状態: pendingが1件あるはず
        app.update_ui_status()
        await pilot.pause()
        
        # Statusウィジェットのテキストを検証
        status_mode = app.query_one("#status_mode")
        status_pending = app.query_one("#status_pending")
        
        assert "MANUAL" in str(status_mode.render())
        assert "1" in str(status_pending.render()) # 1 pending action

@pytest.mark.asyncio
async def test_tui_action_review_modal():
    """DataTableの行を選択したときに詳細モーダルが表示されるかテスト"""
    from phronel_ai_agent.interfaces.tui import ActionDetailModal
    
    app = PhronelApp()
    async with app.run_test() as pilot:
        # Action Reviewタブに切り替え
        tabbed_content = app.query_one(TabbedContent)
        tabbed_content.active = "tab_review"
        await pilot.pause()
        
        # DataTableを取得
        table = app.query_one("#action_table", DataTable)
        assert table is not None
        
        # 最初の行キーを取得
        first_row_key = list(table.rows.keys())[0]
        
        # 行の選択イベント（クリック/Enterに相当）をシミュレート
        table.post_message(DataTable.RowSelected(table, 0, first_row_key))
        await pilot.pause()
        
        # 現在表示されているスクリーンの一番上がActionDetailModalか検証
        assert isinstance(app.screen, ActionDetailModal)
        
        # モーダル内のコンテンツを検証
        modal_content = app.screen.query_one("#modal_content")
        assert modal_content is not None
        # データベースに保存されたレコードのコンテンツが含まれているか確認
        assert "Test" in str(modal_content.render())
        
        # モーダルの「Close」ボタンを押して閉じることを確認
        app.screen.query_one("#btn_close").press()
        await pilot.pause()
        
        # モーダルが閉じているか検証
        assert not isinstance(app.screen, ActionDetailModal)

@pytest.mark.asyncio
async def test_tui_action_approve_and_reject():
    """DataTableの選択された行に対してApprove/Rejectボタンを押したときの挙動をテスト"""
    app = PhronelApp()
    async with app.run_test() as pilot:
        # Action Reviewタブに切り替え
        tabbed_content = app.query_one(TabbedContent)
        tabbed_content.active = "tab_review"
        await pilot.pause()
        
        # DataTableを取得
        table = app.query_one("#action_table", DataTable)
        assert table is not None
        
        # 最初の行にフォーカスを合わせる
        table.cursor_coordinate = (0, 0)
        
        # Approveボタンをプレスする
        await pilot.click("#btn_approve")
        await pilot.pause()
        
        # ログに「approved」メッセージが出力されていることを確認
        log_view = app.query_one("#log_view", RichLog)
        log_content = "".join([strip.text for strip in log_view.lines])
        assert "approved" in log_content.lower()

        # Rejectボタンをプレスする
        await pilot.click("#btn_reject")
        await pilot.pause()
        
        # ログに「rejected」メッセージが出力されていることを確認
        log_content = "".join([strip.text for strip in log_view.lines])
        assert "rejected" in log_content.lower()


@pytest.mark.asyncio
async def test_tui_observe_interval_seconds_config():
    """Test that observe_interval_seconds is correctly loaded and validated in the TUI."""
    from phronel_ai_agent.core.config import config
    
    # 1. Test valid interval (e.g., 60 seconds)
    with patch.object(config, "get", return_value="60"), \
         patch("phronel_ai_agent.interfaces.tui.app.PhronelApp.set_interval") as mock_set_interval:
        app = PhronelApp()
        async with app.run_test() as pilot:
            mock_set_interval.assert_called_with(60, app.background_agent_check)

    # 2. Test interval below minimum (e.g., 5 seconds should be adjusted to 10)
    with patch.object(config, "get", return_value="5"), \
         patch("phronel_ai_agent.interfaces.tui.app.PhronelApp.set_interval") as mock_set_interval:
        app = PhronelApp()
        async with app.run_test() as pilot:
            mock_set_interval.assert_called_with(10, app.background_agent_check)

    # 3. Test invalid interval string (e.g., "invalid", should fallback to 3600)
    with patch.object(config, "get", return_value="invalid"), \
         patch("phronel_ai_agent.interfaces.tui.app.PhronelApp.set_interval") as mock_set_interval:
        app = PhronelApp()
        async with app.run_test() as pilot:
            mock_set_interval.assert_called_with(3600, app.background_agent_check)


