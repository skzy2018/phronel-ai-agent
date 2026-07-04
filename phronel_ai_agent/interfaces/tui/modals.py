import asyncio
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button, Static
from textual.containers import Vertical, ScrollableContainer, Horizontal
from textual import work, on

from ...core.models import ActionLog
from ...services.knowledge import knowledge_base

class ActionDetailModal(ModalScreen[None]):
    """Modal screen for displaying action details."""
    
    def __init__(self, action: ActionLog, **kwargs):
        super().__init__(**kwargs)
        self.action = action

    def compose(self) -> ComposeResult: # type: ignore
        with Vertical(id="modal_container"):
            yield Label(f"Action Detail (ID: {self.action.id})", id="modal_title")
            
            with ScrollableContainer(id="modal_body"):
                yield Label(f"Type: [bold]{self.action.action_type}[/bold]\n"
                            f"Status: [bold]{self.action.status}[/bold]\n"
                            f"Created At: {self.action.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"Target ID: [cyan]{self.action.target_id or 'N/A'}[/cyan]\n"
                            f"Executed At: {self.action.executed_at.strftime('%Y-%m-%d %H:%M:%S') if self.action.executed_at else 'N/A'}",
                            classes="modal_meta")
                
                # Show conversation context if this is a reply or like
                if self.action.action_type in ["reply", "like"] and self.action.target_id:
                    yield Label("\n[bold yellow]Conversation Thread (会話スレッドコンテキスト)[/bold yellow]")
                    yield Static("Loading thread conversation context...", id="modal_thread_loading")
                    
                yield Label("\n[bold green]Proposed Output Text (生成テキスト)[/bold green]")
                yield Static(self.action.content or "", id="modal_content")
            
            with Horizontal(id="modal_buttons"):
                yield Button("Close", id="btn_close", variant="primary")

    def on_mount(self) -> None:
        if self.action.action_type in ["reply", "like"] and self.action.target_id:
            self.load_thread_context()

    @work(exclusive=True)
    async def load_thread_context(self) -> None:
        from ...services.x_client import x_client
        try:
            # 1. Fetch the target root tweet itself to guarantee we show the user's original message
            target_tweet = await asyncio.to_thread(x_client.get_tweet, self.action.target_id)
            
            all_tweets = {}
            if target_tweet:
                all_tweets[target_tweet["id"]] = target_tweet
                conversation_id = target_tweet.get("conversation_id")
            else:
                conversation_id = self.action.target_id
                
            # 2. Fetch any other tweets in this conversation thread
            if conversation_id:
                raw_thread = await asyncio.to_thread(x_client.get_conversation_thread, conversation_id)
                if raw_thread:
                    for t in raw_thread:
                        all_tweets[t["id"]] = t
            
            if all_tweets:
                from ...core.db import get_active_persona
                active_p = get_active_persona()
                persona_name = active_p.name if active_p else "Agent"
                
                # Sort de-duplicated tweets chronologically
                sorted_thread = sorted(all_tweets.values(), key=lambda x: x.get("created_at", ""))
                lines = []
                for t in sorted_thread:
                    text = t.get("text", "").strip()
                    if t.get("is_agent", False):
                        lines.append(f"[bold green]{persona_name} (Agent):[/bold green] {text}")
                    else:
                        lines.append(f"[bold cyan]User:[/bold cyan] {text}")
                
                thread_text = "\n".join(lines)
                self.query_one("#modal_thread_loading", Static).update(thread_text)
            else:
                self.query_one("#modal_thread_loading", Static).update("[dim]No prior conversation history found for this tweet.[/dim]")
        except Exception as e:
            self.query_one("#modal_thread_loading", Static).update(f"[red]Error loading thread context: {e}[/red]")

    @on(Button.Pressed, "#btn_close")
    def close_modal(self) -> None:
        self.dismiss()

class KnowledgeImportModal(ModalScreen[None]):
    """Modal screen for entering a file path or URL to import."""
    
    def compose(self) -> ComposeResult: # type: ignore
        with Vertical(id="modal_container"):
            yield Label("Import Knowledge Material", id="modal_title")
            
            with ScrollableContainer(id="modal_body"):
                yield Label("Please enter a local File Path or Web URL:")
                yield Input(placeholder="e.g. ./docs/faq.md or https://example.com/specs", id="input_kb_path_or_url")
            
            with Horizontal(id="modal_buttons"):
                yield Button("Learn Material", id="btn_modal_learn", variant="success")
                yield Button("Cancel", id="btn_modal_cancel", variant="primary")

    @on(Button.Pressed, "#btn_modal_cancel")
    def cancel(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#btn_modal_learn")
    @work(exclusive=True)
    async def learn_material(self) -> None:
        input_widget = self.query_one("#input_kb_path_or_url", Input)
        target = input_widget.value.strip()
        
        if not target:
            self.notify("Please enter a file path or URL.", severity="error")
            return
            
        self.dismiss() # Close modal first to let user see notifications in main TUI
        
        # Decide if URL or File path
        if target.startswith("http://") or target.startswith("https://"):
            self.app.notify(f"Fetching and analyzing URL '{target}'...")
            try:
                count = await asyncio.to_thread(knowledge_base.add_url, target)
                if count > 0:
                    self.app.notify(f"Successfully learned {count} chunks from URL!", severity="information")
                else:
                    self.app.notify("No content imported from URL.", severity="warning")
            except Exception as e:
                self.app.notify(f"Web URL Ingestion failed: {e}", severity="error")
        else:
            path = Path(target)
            if not path.exists() or not path.is_file():
                self.app.notify(f"File not found: '{target}'", severity="error")
                return
                
            self.app.notify(f"Reading and learning '{path.name}'...")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                count = await asyncio.to_thread(knowledge_base.add_document, content, str(path))
                if count > 0:
                    self.app.notify(f"Successfully learned {count} chunks from file!", severity="information")
                else:
                    self.app.notify("No content imported from file.", severity="warning")
            except Exception as e:
                self.app.notify(f"File Ingestion failed: {e}", severity="error")
                
        # Trigger parent TUI refresh
        try:
            self.app.query_one("#knowledge_base_view").refresh_sources() # type: ignore
        except Exception:
            pass
