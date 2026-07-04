from datetime import datetime
from textual.app import ComposeResult
from textual.widgets import Static, Label, DataTable, Button, RichLog
from textual.containers import Vertical, Horizontal
from textual import on

from ...services.knowledge import knowledge_base
from .modals import KnowledgeImportModal

class KnowledgeBaseView(Static):
    """Screen for viewing, adding, and deleting knowledge sources."""
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Knowledge Base Sources", classes="section_title")
            with Horizontal():
                with Vertical(id="kb_left_pane"):
                    yield DataTable(id="kb_sources_table")
                with Vertical(id="kb_right_pane"):
                    yield Label("Source Content Preview", id="kb_preview_header")
                    yield RichLog(id="kb_chunks_log", highlight=True, wrap=True)
            with Horizontal(id="kb_learn_input_container"):
                yield Button("+ Learn Material (File/URL)", id="btn_kb_add_modal", variant="success")
                yield Button("Delete Selected", id="btn_delete_source", variant="error")
                yield Button("Refresh List", id="btn_kb_refresh", variant="default")

    def on_mount(self) -> None:
        table = self.query_one("#kb_sources_table", DataTable)
        table.add_columns("Source Path/URL", "Chunks", "Imported At")
        table.cursor_type = "row"
        self.refresh_sources()

    def refresh_sources(self) -> None:
        table = self.query_one("#kb_sources_table", DataTable)
        table.clear()
        
        sources = knowledge_base.list_sources()
        for s in sources:
            imported_str = s["imported_at"].strftime("%Y-%m-%d %H:%M") if isinstance(s["imported_at"], datetime) else str(s["imported_at"])
            table.add_row(
                s["source"],
                str(s["chunk_count"]),
                imported_str
            )
            
        # Clean preview if no rows
        if not sources:
            self.query_one("#kb_chunks_log", RichLog).clear()

    @on(DataTable.RowHighlighted, "#kb_sources_table")
    def on_source_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_key = event.row_key
        table = self.query_one("#kb_sources_table", DataTable)
        try:
            source_name = table.get_row(row_key)[0]
            self.preview_source(source_name)
        except Exception as e:
            pass

    def preview_source(self, source_name: str) -> None:
        log = self.query_one("#kb_chunks_log", RichLog)
        log.clear()
        
        chunks = knowledge_base.get_chunks_by_source(source_name)
        log.write(f"[bold green]Previewing {len(chunks)} chunks from {source_name}:[/bold green]\n")
        
        for i, chunk in enumerate(chunks):
            log.write(f"[bold cyan]--- Chunk #{i+1} ---[/bold cyan]\n{chunk.content}\n")

    @on(Button.Pressed, "#btn_kb_refresh")
    def action_kb_refresh(self) -> None:
        self.refresh_sources()
        self.notify("Knowledge list refreshed.")

    @on(Button.Pressed, "#btn_delete_source")
    def action_delete_source(self) -> None:
        table = self.query_one("#kb_sources_table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            source_name = table.get_row(row_key)[0]
            
            deleted_count = knowledge_base.delete_source(source_name)
            self.notify(f"Deleted source and {deleted_count} chunks.", severity="warning")
            self.refresh_sources()
        except Exception as e:
            self.notify(f"Please select a source row to delete. Error: {e}", severity="error")

    @on(Button.Pressed, "#btn_kb_add_modal")
    def action_kb_add_modal(self) -> None:
        self.app.push_screen(KnowledgeImportModal())
