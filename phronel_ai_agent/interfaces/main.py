import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
import logging
import os
import sys

# Setup logging for CLI commands and files
logger = logging.getLogger("phronel")
logger.setLevel(logging.DEBUG)

# File Handler for all commands (including background and CLI runs)
try:
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler("logs/agent.log", encoding="utf-8")
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
except Exception:
    pass

# Console (Stream) Handler - only for CLI commands (excluding TUI 'start')
if len(sys.argv) > 1 and sys.argv[1] != "start":
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    stream_handler.setFormatter(stream_formatter)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

from .tui import PhronelApp
from ..core.db import init_db, get_session, get_actions_by_status
from ..core.config import config
from ..services.knowledge import knowledge_base
from ..skills.brain import brain
from ..skills.executor import approve_action, execute_action
from ..skills.observer import observer

app = typer.Typer()
console = Console()

@app.command()
def start():
    """
    Start the Phronel AI Agent TUI (Textual User Interface).
    """
    console.print("[green]Starting Phronel AI Agent...[/green]")
    # Ensure DB is initialized before starting
    init_db()
    app_tui = PhronelApp()
    app_tui.run()

@app.command()
def init():
    """
    Initialize the Phronel AI Agent.
    Creates the database and prompts for necessary API keys.
    """
    console.print("[bold cyan]Initializing Phronel AI Agent...[/bold cyan]")
    
    try:
        init_db()
        console.print("[green]✔ Database initialized.[/green]")
    except Exception as e:
        console.print(f"[red]✘ Database initialization failed: {e}[/red]")
        return

    console.print("\n[yellow]Please enter your X (Twitter) API credentials.[/yellow]")
    console.print("These will be stored locally in your SQLite database.\n")

    bearer_token = typer.prompt("X Bearer Token", default="")
    api_key = typer.prompt("X API Key (Consumer Key)")
    api_secret = typer.prompt("X API Secret (Consumer Secret)", hide_input=True)
    access_token = typer.prompt("X Access Token")
    access_token_secret = typer.prompt("X Access Token Secret", hide_input=True)

    config.set("x_bearer_token", bearer_token, "X Bearer Token (OAuth 2.0)")
    config.set("x_api_key", api_key, "X Consumer Key")
    config.set("x_api_secret", api_secret, "X Consumer Secret")
    config.set("x_access_token", access_token, "X Access Token")
    config.set("x_access_token_secret", access_token_secret, "X Access Token Secret")

    console.print("\n[yellow]Please enter your LLM Provider credentials.[/yellow]")
    gemini_api_key = typer.prompt("Gemini API Key", default="")
    if gemini_api_key:
        config.set("gemini_api_key", gemini_api_key, "Google Gemini API Key")
    
    # Default execution mode
    mode = typer.prompt("Execution Mode (manual/semi-auto/auto)", default="manual")
    config.set("execution_mode", mode, "Agent operation mode")

    console.print("\n[bold green]✔ Configuration saved successfully![/bold green]")
    console.print("You can now run [bold]phronel start[/bold] to launch the agent.")

@app.command()
def config_cmd(key: str = typer.Argument(None), value: str = typer.Argument(None)):
    """
    View or update configuration settings.
    Usage: phronel config [key] [value]
    """
    init_db() # Ensure DB exists
    
    if key and value:
        config.set(key, value)
        console.print(f"[green]Updated {key} = {value}[/green]")
    elif key:
        val = config.get(key)
        if val:
            console.print(f"[cyan]{key}:[/cyan] {val}")
        else:
            console.print(f"[red]Key '{key}' not found.[/red]")
    else:
        console.print("[yellow]Please provide a key to view or key/value to update.[/yellow]")

app.command(name="config")(config_cmd)

@app.command()
def learn(file_path: str):
    """
    Import knowledge from a text file (Markdown, TXT).
    Usage: phronel learn ./docs/product_info.md
    """
    init_db()
    path = Path(file_path)
    
    if not path.exists():
        console.print(f"[red]Error: File '{file_path}' not found.[/red]")
        raise typer.Exit(code=1)
    
    if not path.is_file():
        console.print(f"[red]Error: '{file_path}' is not a file.[/red]")
        raise typer.Exit(code=1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        console.print(f"[cyan]Reading '{path.name}'...[/cyan]")
        count = knowledge_base.add_document(content=content, source=str(path))
        
        if count > 0:
            console.print(f"[green]✔ Successfully imported {count} chunks from '{path.name}'.[/green]")
        else:
            console.print(f"[yellow]⚠ No content imported (file might be empty).[/yellow]")

    except Exception as e:
        console.print(f"[red]Error processing file: {e}[/red]")
        raise typer.Exit(code=1)

@app.command(name="learn-list")
def learn_list():
    """
    List all currently imported knowledge sources and chunk counts.
    Usage: phronel learn-list
    """
    from datetime import datetime
    init_db()
    sources = knowledge_base.list_sources()
    
    if not sources:
        console.print("[yellow]No knowledge sources found. Use 'phronel learn <file>' to import some.[/yellow]")
        return

    table = Table(title="Imported Knowledge Sources")
    table.add_column("Source (File Path/URL)", style="cyan", no_wrap=True)
    table.add_column("Chunks", style="magenta", justify="right")
    table.add_column("Imported At (UTC)", style="green")

    for s in sources:
        imported_str = s["imported_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(s["imported_at"], datetime) else str(s["imported_at"])
        table.add_row(s["source"], str(s["chunk_count"]), imported_str)

    console.print(table)

@app.command(name="learn-remove")
def learn_remove(source: str):
    """
    Delete an imported knowledge source and its chunks.
    Usage: phronel learn-remove "./docs/product_info.md"
    """
    init_db()
    console.print(f"[cyan]Deleting source '{source}'...[/cyan]")
    deleted_count = knowledge_base.delete_source(source)
    
    if deleted_count > 0:
        console.print(f"[green]✔ Successfully deleted source and all {deleted_count} associated chunks.[/green]")
    else:
        console.print(f"[red]Error: Source '{source}' not found or had 0 chunks.[/red]")

@app.command(name="learn-url")
def learn_url(url: str):
    """
    Import knowledge from a web URL (HTML plain text).
    Usage: phronel learn-url "https://example.com/info"
    """
    init_db()
    console.print(f"[cyan]Fetching and analyzing URL '{url}'...[/cyan]")
    try:
        count = knowledge_base.add_url(url)
        if count > 0:
            console.print(f"[green]✔ Successfully imported {count} chunks from URL '{url}'.[/green]")
        else:
            console.print(f"[yellow]⚠ No content imported from URL '{url}'.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error fetching URL: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def propose(topic: Optional[str] = typer.Argument(None, help="The topic for the tweet proposal. Defaults to active persona's topic.")):
    """
    Generate a tweet proposal based on a topic and save as pending action.
    Usage: phronel propose "New product launch"
    """
    init_db()
    if not topic:
        from ..core.db import get_active_persona
        active_p = get_active_persona()
        topic = getattr(active_p, "tweet_topic", "Latest updates on the Phronel AI Agent") or "Latest updates on the Phronel AI Agent"
        console.print(f"[cyan]Generating proposal using active persona ({active_p.name}) topic: '{topic}'...[/cyan]")
    else:
        console.print(f"[cyan]Generating proposal for topic: '{topic}'...[/cyan]")
        
    action = brain.create_tweet_proposal(topic)
    console.print(f"[green]✔ Proposal created![/green]")
    console.print(f"[bold]ID:[/bold] {action.id}")
    console.print(f"[bold]Content:[/bold] {action.content}")

@app.command()
def observe(keyword: str, max_results: Optional[int] = None):
    """
    Observe X for a specific keyword, analyze trends, and generate a proposal.
    Usage: phronel observe "AI Agent"
    """
    init_db()
    console.print(f"[cyan]Observing X for '{keyword}'...[/cyan]")
    action = observer.observe_keyword(keyword, max_results)
    
    if action:
        console.print(f"\n[bold green]✔ Analysis Complete and Proposal Created![/bold green]")
        console.print(f"[bold]Action ID:[/bold] {action.id}")
        console.print(f"[bold]Proposal Type:[/bold] {action.action_type}")
        console.print(f"[bold]Content:[/bold]\n{action.content}")
        console.print("\n[dim]Run 'phronel approve' to review it.[/dim]")
    else:
        console.print(f"[yellow]No actionable insights or proposals generated for '{keyword}'.[/yellow]")

@app.command(name="observe-mentions")
def observe_mentions_cmd(max_results: Optional[int] = typer.Option(None, help="The maximum number of mentions to fetch.")):
    """
    Observe X for mentions of your account, analyze and generate a reply proposal.
    Usage: phronel observe-mentions
    """
    init_db()
    console.print(f"[cyan]Observing X for account mentions...[/cyan]")
    action = observer.observe_mentions(max_results)
    
    if action:
        console.print(f"\n[bold green]✔ Analysis Complete and Proposal Created![/bold green]")
        console.print(f"[bold]Action ID:[/bold] {action.id}")
        console.print(f"[bold]Proposal Type:[/bold] {action.action_type}")
        console.print(f"[bold]Content:[/bold]\n{action.content}")
        console.print("\n[dim]Run 'phronel approve' to review it.[/dim]")
    else:
        console.print(f"[yellow]No actionable insights or proposals generated for mentions.[/yellow]")

@app.command()
def actions(status: str = typer.Argument("pending")):
    """
    List actions filtered by status (pending, approved, executed, failed).
    """
    init_db()
    table = Table(title=f"Phronel Actions ({status})")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Content", style="green", no_wrap=False)
    table.add_column("Status", style="yellow")
    table.add_column("Created At", style="blue")

    results = get_actions_by_status([status])
    for action in results:
        table.add_row(
            str(action.id),
            action.action_type,
            (action.content or "")[:100] + "..." if len(action.content or "") > 100 else (action.content or ""),
            action.status,
            action.created_at.strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(table)

@app.command()
def approve(action_id: int):
    """
    Approve a pending action.
    Usage: phronel approve 1
    """
    init_db()
    action = approve_action(action_id)
    if action:
        console.print(f"[green]✔ Action {action_id} approved.[/green]")
    else:
        console.print(f"[red]✘ Could not approve action {action_id}. Not found or not pending.[/red]")

@app.command()
def execute(action_id: int):
    """
    Execute an approved action (posts to X).
    Usage: phronel execute 1
    """
    init_db()
    action = execute_action(action_id)
    if action and action.status == "executed":
        console.print(f"[bold green]✔ Action {action_id} executed successfully![/bold green]")
    elif action:
        console.print(f"[yellow]⚠ Action {action_id} finished with status: {action.status}[/yellow]")
    else:
        console.print(f"[red]✘ Could not execute action {action_id}.[/red]")

@app.command()
def report():
    """
    Generate a daily report of the agent's activities and strategies.
    Usage: phronel report
    """
    init_db()
    console.print("[cyan]Generating daily report...[/cyan]")
    from ..skills.analyst import analyst
    report_text = analyst.generate_daily_report()
    console.print("\n[bold]Daily Report:[/bold]")
    console.print(report_text)

@app.command()
def optimize():
    """
    Run DSPy Optimizer to improve prompt generation based on past performance.
    Usage: phronel optimize
    """
    init_db()
    console.print("[cyan]Running prompt optimization...[/cyan]")
    from ..skills.analyst import analyst
    success = analyst.optimize_creator_prompts()
    if success:
        console.print("[bold green]✔ Optimization completed successfully![/bold green]")
    else:
        console.print("[bold red]✘ Optimization failed.[/bold red]")

if __name__ == "__main__":
    app()
