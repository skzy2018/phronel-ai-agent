from textual.app import ComposeResult
from textual.widgets import Static, Label, DataTable, Button, Input
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual import on

from ...core.db import (
    list_personas, get_active_persona, update_persona, add_persona,
    activate_persona, delete_persona
)

class PersonaSettingsView(Static):
    """Screen for managing, adding, editing, deleting, and activating AI Persona configurations."""
    
    # Store the currently selected persona's database ID
    selected_persona_id = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("AI Agent Identity & Strategy Settings", classes="section_title")
            with Horizontal():
                with Vertical(id="persona_left_pane"):
                    yield Label("Registered Personas", id="persona_list_header")
                    yield DataTable(id="persona_list_table")
                with Vertical(id="persona_right_pane"):
                    yield Label("Edit Selected Persona", id="persona_edit_header")
                    with ScrollableContainer(id="persona_form_container"):
                        yield Label("Agent Name (名前)", classes="form_label")
                        yield Input(placeholder="e.g. Phronel", id="input_persona_name")
                        
                        yield Label("Professional Role (役割・専門性)", classes="form_label")
                        yield Input(placeholder="e.g. SNS Sales Representative...", id="input_persona_role")
                        
                        yield Label("Tone of Voice (口調・トーン)", classes="form_label")
                        yield Input(placeholder="e.g. Professional, polite, helpful...", id="input_persona_tone")
                        
                        yield Label("Constraints (送信制約・足切りルール)", classes="form_label")
                        yield Input(placeholder="e.g. Max 280 chars. Use emoji sparingly...", id="input_persona_constraints")
                        
                        yield Label("Sales Strategy Guideline (営業戦略・行動規範)", classes="form_label")
                        yield Input(placeholder="e.g. Focus on providing value and solving pain points...", id="input_persona_strategy")
                        
                        yield Label("Search Keywords - comma separated (検索キーワード - カンマ区切り)", classes="form_label")
                        yield Input(placeholder="e.g. AI, Python, LLM", id="input_persona_keywords")
                        
                        yield Label("Tweet Topic for 'Run Propose' (発信トピック - Run Propose用)", classes="form_label")
                        yield Input(placeholder="e.g. Latest updates on the Phronel AI Agent", id="input_persona_tweet_topic")
                        
            with Horizontal(id="persona_buttons_container"):
                yield Button("Save Changes", id="btn_save_persona", variant="success")
                yield Button("Add New Persona", id="btn_add_persona", variant="primary")
                yield Button("Activate Selected", id="btn_activate_persona", variant="warning")
                yield Button("Delete Selected", id="btn_delete_persona", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#persona_list_table", DataTable)
        table.add_columns("ID", "Name", "Active?")
        table.cursor_type = "row"
        self.refresh_personas()

    def refresh_personas(self) -> None:
        """Refreshes the left pane DataTable of personas and loads the active one first if none selected."""
        table = self.query_one("#persona_list_table", DataTable)
        table.clear()
        
        personas = list_personas()
        for p in personas:
            table.add_row(
                str(p.id),
                p.name,
                "★ Active" if p.is_active else "Inactive"
            )
            
        # Select active persona on startup if nothing is selected
        if self.selected_persona_id is None:
            active_p = get_active_persona()
            if active_p and active_p.id:
                self.selected_persona_id = active_p.id
                
        self.load_selected_persona()

    def load_selected_persona(self) -> None:
        """Fills input fields with the selected persona's details."""
        if self.selected_persona_id is None:
            return
            
        personas = list_personas()
        selected = next((p for p in personas if p.id == self.selected_persona_id), None)
        
        if selected:
            self.query_one("#input_persona_name", Input).value = selected.name
            self.query_one("#input_persona_role", Input).value = selected.role
            self.query_one("#input_persona_tone", Input).value = selected.tone
            self.query_one("#input_persona_constraints", Input).value = selected.constraints
            self.query_one("#input_persona_strategy", Input).value = selected.sales_strategy
            self.query_one("#input_persona_keywords", Input).value = selected.observe_keyword or ""
            self.query_one("#input_persona_tweet_topic", Input).value = getattr(selected, "tweet_topic", "Latest updates on the Phronel AI Agent") or "Latest updates on the Phronel AI Agent"
            
            # Show active status in header
            status_text = " ★ Active" if selected.is_active else ""
            self.query_one("#persona_edit_header", Label).update(f"Edit Selected Persona: [bold cyan]{selected.name}[/bold cyan]{status_text}")

    @on(DataTable.RowHighlighted, "#persona_list_table")
    def on_persona_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_key = event.row_key
        table = self.query_one("#persona_list_table", DataTable)
        try:
            p_id_str = table.get_row(row_key)[0]
            self.selected_persona_id = int(p_id_str)
            self.load_selected_persona()
        except Exception as e:
            pass

    @on(Button.Pressed, "#btn_save_persona")
    def save_settings(self) -> None:
        """Saves current input values to the currently selected persona."""
        if self.selected_persona_id is None:
            self.notify("No persona selected.", severity="error")
            return
            
        name = self.query_one("#input_persona_name", Input).value.strip()
        role = self.query_one("#input_persona_role", Input).value.strip()
        tone = self.query_one("#input_persona_tone", Input).value.strip()
        constraints = self.query_one("#input_persona_constraints", Input).value.strip()
        strategy = self.query_one("#input_persona_strategy", Input).value.strip()
        keywords = self.query_one("#input_persona_keywords", Input).value.strip()
        tweet_topic = self.query_one("#input_persona_tweet_topic", Input).value.strip()
        
        if not name:
            self.notify("Agent Name cannot be empty.", severity="error")
            return

        update_persona(
            self.selected_persona_id,
            name=name,
            role=role,
            tone=tone,
            constraints=constraints,
            sales_strategy=strategy,
            observe_keyword=keywords if keywords else None,
            tweet_topic=tweet_topic if tweet_topic else "Latest updates on the Phronel AI Agent"
        )
        
        self.notify("Selected Persona saved successfully!", severity="information")
        self.refresh_personas()

    @on(Button.Pressed, "#btn_add_persona")
    def create_new_persona(self) -> None:
        """Creates a new persona with dummy template and opens it for editing."""
        new_p = add_persona(
            name="New Persona",
            role="AI Specialist",
            tone="Professional, polite",
            constraints="Max 280 chars",
            sales_strategy="Focus on solving pain points."
        )
        self.selected_persona_id = new_p.id
        self.notify("New Persona template created! Edit fields and click Save Changes.", severity="warning")
        self.refresh_personas()

    @on(Button.Pressed, "#btn_activate_persona")
    def action_activate_persona(self) -> None:
        """Sets the selected persona as the active one."""
        if self.selected_persona_id is None:
            self.notify("No persona selected.", severity="error")
            return
            
        success = activate_persona(self.selected_persona_id)
        if success:
            self.notify("Persona activated successfully!", severity="information")
            self.refresh_personas()
        else:
            self.notify("Failed to activate persona.", severity="error")

    @on(Button.Pressed, "#btn_delete_persona")
    def action_delete_persona(self) -> None:
        """Deletes the selected persona, unless it is active."""
        if self.selected_persona_id is None:
            self.notify("No persona selected.", severity="error")
            return
            
        success = delete_persona(self.selected_persona_id)
        if success:
            self.notify("Persona deleted.", severity="warning")
            # Clear selected ID and refresh list to select the active one
            self.selected_persona_id = None
            self.refresh_personas()
        else:
            self.notify("Cannot delete the active persona. Please activate another one first.", severity="error")
