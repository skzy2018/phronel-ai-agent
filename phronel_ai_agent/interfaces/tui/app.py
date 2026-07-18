import asyncio
import logging

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Button, TabbedContent, TabPane, DataTable
from textual.containers import Horizontal, ScrollableContainer
from textual import work, on
from textual.binding import Binding

from ...core.config import config
from ...core.db import get_pending_action_count, update_action_status
from ...skills.executor import execute_action, approve_action
from ...skills.observer import observer
from ...skills.brain import brain
from ...skills.analyst import analyst

from .dashboard_view import AgentStatus
from .review_view import ActionReview
from .knowledge_view import KnowledgeBaseView
from .persona_view import PersonaSettingsView

# --- Custom Logging Handler for TUI ---
class TuiLogHandler(logging.Handler):
    def __init__(self, log_widget: RichLog):
        super().__init__()
        self.log_widget = log_widget
        self.history = []

    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.log_widget.write(log_entry)
            self.history.append(log_entry)
            if len(self.history) > 1000:
                self.history.pop(0)
        except Exception:
            # Prevent throwing NoActiveAppError or other issues when running tests
            # or when the logger is triggered outside an active Textual application
            pass

class PhronelApp(App):
    """Phronel AI Agent TUI Application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    .section_title {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #log_view {
        height: 1fr;
        border: solid green;
    }

    #status_container {
        width: 30;
        border: solid white;
        padding: 0 1;
        height: 1fr;
        overflow-y: auto;
    }

    #status_container Button {
        height: 3;
        margin-top: 1;
        width: 100%;
        border: none;
    }

    AgentStatus {
        height: auto;
        margin-bottom: 1;
    }

    AgentStatus Vertical {
        height: auto;
    }

    #action_table {
        height: 1fr;
        border: solid blue;
    }

    #action_buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    #action_buttons Button {
        margin: 0 1;
    }

    #status_header {
        text-style: underline;
        margin-bottom: 1;
    }

    ActionDetailModal {
        align: center middle;
    }

    #modal_container {
        width: 80;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #modal_title {
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
        padding: 1;
    }

    #modal_body {
        height: 1fr;
        margin-bottom: 1;
    }

    .modal_meta {
        margin-bottom: 1;
    }

    #modal_content {
        border: solid $accent;
        padding: 1;
        height: auto;
    }

    #modal_buttons {
        height: 3;
        align: center middle;
    }

    #kb_left_pane {
        width: 45%;
        height: 1fr;
        border: solid green;
        margin-right: 1;
    }

    #kb_right_pane {
        width: 55%;
        height: 1fr;
        border: solid cyan;
    }

    #kb_preview_header {
        text-style: bold;
        background: $accent;
        color: $text;
        text-align: center;
        width: 100%;
        padding: 1;
    }

    #kb_chunks_log {
        height: 1fr;
        background: $surface-darken-1;
    }

    #kb_learn_input_container {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    #kb_learn_input_container Button {
        margin: 0 1;
    }

    #persona_left_pane {
        width: 35%;
        height: 1fr;
        border: solid green;
        margin-right: 1;
    }

    #persona_right_pane {
        width: 65%;
        height: 1fr;
        border: solid cyan;
    }

    #persona_list_header {
        text-style: bold;
        background: $accent;
        color: $text;
        text-align: center;
        width: 100%;
        padding: 1;
    }

    #persona_list_table {
        height: 1fr;
    }

    #persona_edit_header {
        text-style: bold;
        background: $primary;
        color: $text;
        text-align: center;
        width: 100%;
        padding: 1;
    }

    #persona_form_container {
        height: 1fr;
        padding: 1;
    }

    .form_label {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        width: 100%;
    }

    #persona_buttons_container {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    #persona_buttons_container Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh Data", show=True),
        Binding("s", "start_agent", "Run Agent Cycle", show=True),
        Binding("c", "copy_logs", "Copy Logs", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Dashboard", id="tab_dashboard"):
                with Horizontal():
                    yield RichLog(id="log_view", highlight=True, wrap=True, markup=True)
                    with ScrollableContainer(id="status_container"):
                        yield AgentStatus(id="agent_status")
                        yield Button("Run Observe", id="btn_observe", variant="primary")
                        yield Button("Run Propose", id="btn_propose", variant="default")
                        yield Button("Generate Report", id="btn_report", variant="success")
                        yield Button("Run Optimizer", id="btn_optimize", variant="warning")
            with TabPane("Action Review", id="tab_review"):
                yield ActionReview(id="action_review")
            with TabPane("Knowledge Base", id="tab_knowledge"):
                yield KnowledgeBaseView(id="knowledge_base_view")
            with TabPane("Persona Settings", id="tab_persona"):
                yield PersonaSettingsView(id="persona_settings_view")
        yield Footer()

    def on_mount(self) -> None:
        self.log_view = self.query_one("#log_view", RichLog)
        
        # Setup Logger
        self.handler = TuiLogHandler(self.log_view)
        self.handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
        logger = logging.getLogger("phronel")
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)
        
        self.log_view.write("[bold yellow]Phronel AI Agent TUI Started.[/bold yellow]")
        self.update_ui_status()
        
        # Start background check interval (configurable, defaults to 1 hour)
        interval_str = config.get("observe_interval_seconds", default="3600")
        try:
            interval = int(interval_str)
            if interval < 10:
                logger.warning(f"Observe interval ({interval}s) is too short. Resetting to 10s minimum for stability.")
                interval = 10
        except ValueError:
            logger.warning(f"Invalid observe_interval_seconds configuration value '{interval_str}'. Falling back to 3600s.")
            interval = 3600

        self.set_interval(interval, self.background_agent_check)

    def update_ui_status(self) -> None:
        """Updates the status display and action review table."""
        mode = config.get("execution_mode", default="manual") or "manual"
        pending_count = get_pending_action_count()
        
        self.query_one("#agent_status", AgentStatus).update_status(mode, pending_count)
        try:
            self.query_one("#action_review", ActionReview).refresh_actions()
        except Exception:
            pass # Pane might not be mounted yet
        try:
            self.query_one("#knowledge_base_view", KnowledgeBaseView).refresh_sources()
        except Exception:
            pass # Pane might not be mounted yet
        try:
            self.query_one("#persona_settings_view", PersonaSettingsView).refresh_personas()
        except Exception:
            pass # Pane might not be mounted yet

    @on(Button.Pressed, "#btn_refresh")
    def action_refresh(self) -> None:
        self.update_ui_status()
        self.log_view.write("Data refreshed.")

    @on(TabbedContent.TabActivated)
    def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Automatically refreshes data when transitioning between tabs."""
        self.update_ui_status()

    @on(Button.Pressed, "#btn_observe")
    @work(exclusive=True)
    async def run_observe(self) -> None:
        # Prioritize active persona's specific keywords
        from ...core.db import get_active_persona
        active_p = get_active_persona()
        keyword = active_p.observe_keyword if active_p else None
        
        if not keyword:
            keyword = config.get("observe_keyword", default="AI Agent")
            
        self.log_view.write(f"[bold cyan]Running Observe for: {keyword}...[/bold cyan]")
        try:
            action = await asyncio.to_thread(observer.observe_keyword, keyword) # type: ignore
            if action:
                self.log_view.write(f"[bold green]Proposal generated (ID: {action.id})[/bold green]")
                await self._handle_auto_execution(action.id) # type: ignore
            else:
                self.log_view.write("[yellow]No proposal generated.[/yellow]")
        except Exception as e:
            self.log_view.write(f"[bold red]Error in Observe: {e}[/bold red]")
        self.update_ui_status()

    @on(Button.Pressed, "#btn_propose")
    @work(exclusive=True)
    async def run_propose(self) -> None:
        from ...core.db import get_active_persona
        active_p = get_active_persona()
        topic = getattr(active_p, "tweet_topic", "Latest updates on the Phronel AI Agent") or "Latest updates on the Phronel AI Agent"
        
        self.log_view.write(f"[bold cyan]Running Propose for active persona ({active_p.name}) with topic: {topic}...[/bold cyan]")
        try:
            action = await asyncio.to_thread(brain.create_tweet_proposal, topic)
            self.log_view.write(f"[bold green]Proposal generated (ID: {action.id})[/bold green]")
            await self._handle_auto_execution(action.id) # type: ignore
        except Exception as e:
            self.log_view.write(f"[bold red]Error in Propose: {e}[/bold red]")
        self.update_ui_status()

    @on(Button.Pressed, "#btn_report")
    @work(exclusive=True)
    async def run_report(self) -> None:
        self.log_view.write("[bold cyan]Generating Daily Report...[/bold cyan]")
        try:
            report_text = await asyncio.to_thread(analyst.generate_daily_report)
            self.log_view.write(f"\n[bold green]--- Daily Report ---[/bold green]\n{report_text}\n[bold green]--------------------[/bold green]\n")
        except Exception as e:
            self.log_view.write(f"[bold red]Error generating report: {e}[/bold red]")

    @on(Button.Pressed, "#btn_optimize")
    @work(exclusive=True)
    async def run_optimize(self) -> None:
        self.log_view.write("[bold cyan]Running Prompt Optimizer...[/bold cyan]")
        try:
            success = await asyncio.to_thread(analyst.optimize_creator_prompts)
            if success:
                self.log_view.write("[bold green]Optimization complete! New prompts saved.[/bold green]")
                # Reload prompts into the brain
                await asyncio.to_thread(brain._load_optimized_prompts)
            else:
                self.log_view.write("[bold red]Optimization failed or aborted.[/bold red]")
        except Exception as e:
            self.log_view.write(f"[bold red]Error running optimizer: {e}[/bold red]")

    async def _handle_auto_execution(self, action_id: int) -> None:
        """Helper method to automatically execute an action if mode is auto."""
        mode = config.get("execution_mode", default="manual") or "manual"
        if mode == "auto":
            self.log_view.write(f"[dim]Auto-mode: Executing action {action_id} immediately...[/dim]")
            executed_action = await asyncio.to_thread(execute_action, action_id)
            if executed_action and executed_action.status == "executed":
                self.log_view.write(f"[bold green]Auto-mode: Action {action_id} executed successfully.[/bold green]")
            else:
                self.log_view.write(f"[bold red]Auto-mode: Action {action_id} failed to execute.[/bold red]")

    @on(Button.Pressed, "#btn_approve")
    def action_approve_selected(self) -> None:
        table = self.query_one("#action_table", DataTable) # type: ignore
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            action_id = int(table.get_row(row_key)[0])
            approve_action(action_id)
            self.log_view.write(f"Action {action_id} approved.")
            self.update_ui_status()
        except Exception as e:
            self.notify(f"Please select a row. Error: {e}", severity="error")

    @on(Button.Pressed, "#btn_execute")
    @work(exclusive=True)
    async def action_execute_selected(self) -> None:
        table = self.query_one("#action_table", DataTable) # type: ignore
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            action_id = int(table.get_row(row_key)[0])
            self.log_view.write(f"Executing action {action_id}...")
            action = await asyncio.to_thread(execute_action, action_id)
            if action and action.status == "executed":
                self.log_view.write(f"[bold green]Action {action_id} executed successfully![/bold green]")
            else:
                self.log_view.write(f"[bold red]Action {action_id} failed or skipped.[/bold red]")
            self.update_ui_status()
        except Exception as e:
            self.notify(f"Please select a row. Error: {e}", severity="error")

    @on(Button.Pressed, "#btn_reject")
    def action_reject_selected(self) -> None:
        table = self.query_one("#action_table", DataTable) # type: ignore
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            action_id = int(table.get_row(row_key)[0])
            update_action_status(action_id, "failed")
            self.log_view.write(f"Action {action_id} rejected.")
            self.update_ui_status()
        except Exception as e:
            self.notify(f"Please select a row. Error: {e}", severity="error")

    async def background_agent_check(self) -> None:
        """Periodic check for auto/semi-auto execution mode."""
        mode = config.get("execution_mode", default="manual") or "manual"
        
        if mode == "manual":
            return

        self.log_view.write(f"[dim]Background cycle started ({mode} mode)...[/dim]")
        
        # Prioritize active persona's specific keywords
        from ...core.db import get_active_persona
        active_p = get_active_persona()
        keyword = active_p.observe_keyword if active_p else None
        
        if not keyword:
            keyword = config.get("observe_keyword", default="AI Agent")
        
        try:
            action = await asyncio.to_thread(observer.observe_keyword, keyword) # type: ignore
            
            if action:
                self.log_view.write(f"[bold green]Background: New proposal generated (ID: {action.id})[/bold green]")
                if mode == "auto":
                    self.log_view.write(f"[dim]Auto-mode: Executing action {action.id} immediately...[/dim]")
                    executed_action = await asyncio.to_thread(execute_action, action.id) # type: ignore
                    if executed_action and executed_action.status == "executed":
                        self.log_view.write(f"[bold green]Auto-mode: Action {action.id} executed successfully.[/bold green]")
                    else:
                        self.log_view.write(f"[bold red]Auto-mode: Action {action.id} failed to execute.[/bold red]")
                else:
                    self.log_view.write(f"[yellow]Semi-auto mode: Action {action.id} is pending review.[/yellow]")
            else:
                self.log_view.write("[dim]Background: No new actions proposed in this cycle.[/dim]")
                
        except Exception as e:
            self.log_view.write(f"[bold red]Background task error: {e}[/bold red]")
        
        self.update_ui_status()

    def action_start_agent(self) -> None:
        """Manual trigger for one cycle."""
        self.run_observe()

    def action_copy_logs(self) -> None:
        """Copies all session dashboard logs (stripped of markup) to the system clipboard."""
        if hasattr(self, "handler") and self.handler.history:
            import re
            clean_lines = []
            for line in self.handler.history:
                # Remove Textual/Rich markup tags like [bold red] for clean text copy
                clean_line = re.sub(r"\[/?(?:bold|dim|italic|underline|reverse|strike|blink|[^\]]+)\]", "", line)
                clean_lines.append(clean_line)
            
            log_text = "\n".join(clean_lines)
            try:
                self.copy_to_clipboard(log_text)
                self.notify("Dashboard logs copied to clipboard!", severity="information")
            except Exception as e:
                self.notify(f"Failed to copy logs: {e}", severity="error")
        else:
            self.notify("No logs to copy yet.", severity="warning")

if __name__ == "__main__":
    app = PhronelApp()
    app.run()
