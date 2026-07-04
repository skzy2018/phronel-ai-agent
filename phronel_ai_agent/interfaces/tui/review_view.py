from textual.app import ComposeResult
from textual.widgets import Static, Label, DataTable, Button
from textual.containers import Vertical, Horizontal
from textual import on

from ...core.db import get_actions_by_status, get_session
from ...core.models import ActionLog
from .modals import ActionDetailModal

class ActionReview(Static):
    """Screen for reviewing and approving pending actions."""
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Pending Actions for Review", classes="section_title")
            yield DataTable(id="action_table")
            with Horizontal(id="action_buttons"):
                yield Button("Refresh", id="btn_refresh", variant="primary")
                yield Button("Approve Selected", id="btn_approve", variant="success")
                yield Button("Execute Selected", id="btn_execute", variant="warning")
                yield Button("Reject Selected", id="btn_reject", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#action_table", DataTable)
        table.add_columns("ID", "Type", "Content", "Status", "Created At")
        table.cursor_type = "row"
        self.refresh_actions()

    def refresh_actions(self) -> None:
        table = self.query_one("#action_table", DataTable)
        table.clear()
        
        actions = get_actions_by_status(["pending", "approved"])
        for action in actions:
            table.add_row(
                str(action.id),
                action.action_type,
                (action.content or "")[:50] + "..." if len(action.content or "") > 50 else (action.content or ""),
                action.status,
                action.created_at.strftime("%H:%M:%S")
            )

    @on(DataTable.RowSelected, "#action_table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        table = self.query_one("#action_table", DataTable)
        try:
            # First column is the action ID
            action_id = int(table.get_row(row_key)[0])
            with get_session() as session:
                action = session.get(ActionLog, action_id)
                if action:
                    self.app.push_screen(ActionDetailModal(action))
        except Exception as e:
            self.notify(f"Failed to open action details: {e}", severity="error")
