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
                            f"Executed At: {self.action.executed_at.strftime('%Y-%m-%d %H:%M:%S') if self.action.executed_at else 'N/A'}",
                            classes="modal_meta")
                yield Static(self.action.content or "", id="modal_content")
            
            with Horizontal(id="modal_buttons"):
                yield Button("Close", id="btn_close", variant="primary")

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
            self.app.query_one("#knowledge_base_view").refresh_sources()
        except Exception:
            pass
