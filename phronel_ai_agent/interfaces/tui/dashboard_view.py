from typing import Optional
from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical

class AgentStatus(Static):
    """Displays the current status of the agent."""
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Agent Status", id="status_header")
            yield Static("Mode: [bold blue]Manual[/bold blue]", id="status_mode")
            yield Static("Pending Actions: [bold yellow]0[/bold yellow]", id="status_pending")
            yield Static("Last Run: [dim]Never[/dim]", id="status_last_run")

    def update_status(self, mode: str, pending_count: int, last_run: Optional[str] = None):
        self.query_one("#status_mode", Static).update(f"Mode: [bold blue]{mode.upper()}[/bold blue]")
        self.query_one("#status_pending", Static).update(f"Pending Actions: [bold yellow]{pending_count}[/bold yellow]")
        if last_run:
            self.query_one("#status_last_run", Static).update(f"Last Run: [dim]{last_run}[/dim]")
