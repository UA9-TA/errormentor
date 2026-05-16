from typing import Optional

import typer
from rich.prompt import Confirm

from .analyzer import Analyzer
from .config import Config
from .context_builder import ContextBuilder
from .display import Display, console
from .git_correlator import GitCorrelator
from .log_parser import LogParser
from .patcher import Patcher
from .spike_detector import SpikeDetector

app = typer.Typer(help="Auto-diagnose production errors by correlating logs with recent commits and AI analysis")

@app.command()
def analyze(
    log_file: str = typer.Argument(..., help="Path to the log file to analyze"),
    correlate: bool = typer.Option(False, "--correlate", help="Correlate spike with git commits"),
    tail: bool = typer.Option(False, "--tail", help="Live tail mode (not implemented yet)"),
    file: Optional[str] = typer.Option(None, "--file", help="Alias for log_file"),
    datadog: Optional[str] = typer.Option(None, "--datadog", help="Datadog query (not implemented yet)"),
    since: Optional[str] = typer.Option(None, "--since", help="Time range (not implemented yet)"),
):
    """Analyze a log file or error stream."""

    # In case --file is used instead of argument
    target_file = file if file else log_file

    if not target_file:
         console.print("[red]Error: log file required[/red]")
         raise typer.Exit(1)

    _run_analysis(target_file, correlate)

@app.command()
def diagnose(log_file: str = typer.Argument(..., help="Path to the log file to analyze")):
    """Show the diagnosis for a log file."""
    _run_analysis(log_file, True)

@app.command()
def fix(log_file: str = typer.Argument(..., help="Path to the log file to analyze")):
    """Auto-generate a fix suggestion for a log file."""
    _run_analysis(log_file, True, auto_prompt_fix=True)


def _run_analysis(log_file: str, correlate: bool, auto_prompt_fix: bool = True):
    config = Config()

    # 1. Parse Logs
    parser = LogParser()
    try:
        events = parser.parse_file(log_file)
    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {log_file}[/red]")
        raise typer.Exit(1)

    if not events:
        console.print("[yellow]No errors found or parsed in log file.[/yellow]")
        raise typer.Exit(0)

    unique_types = len(set(e.error_type for e in events if e.error_type))

    # 2. Detect Spike
    detector = SpikeDetector()
    spike = detector.detect(events)

    if not spike:
         console.print("[yellow]No error spike detected.[/yellow]")
         raise typer.Exit(0)

    # Find the most common message for the spiked error type
    spike_events = [e for e in events if e.error_type == spike.error_type or e.message.startswith(spike.error_type)]
    msg_counts = {}
    for e in spike_events:
         msg_counts[e.message] = msg_counts.get(e.message, 0) + 1
    top_message = max(msg_counts, key=msg_counts.get) if msg_counts else spike.error_type

    # 3. Correlate with Git
    commit_info = None
    files_touched = []
    if correlate:
        correlator = GitCorrelator()
        commit_info = correlator.correlate(spike.spike_started_at)
        if commit_info:
            files_touched = commit_info.files_touched

    # 4. Build Context
    context_builder = ContextBuilder()

    # Get file locations from spike events
    locations = []
    for e in spike_events:
        for loc in e.file_locations:
             if loc not in locations:
                  locations.append(loc)

    source_context = context_builder.build_source_context(locations)

    git_context = "No commit correlation performed."
    if commit_info:
         git_context = context_builder.build_git_context(files_touched)

    # 5. Analyze with Claude
    api_key = config.get_api_key()
    if not api_key:
         console.print("[yellow]Warning: ANTHROPIC_API_KEY not found. Using dummy analysis for demo.[/yellow]")
         # Provide a mock response so tests/demo can run without API key
         analysis = {
            "root_cause": "datetime.now() uses local time (IST) to compare against UTC JWT exp field — all tokens appear expired on non-UTC servers",
            "location": "auth/validators.py:147",
            "explanation": "The commit 'migrate auth to new token service' introduced a bug where datetime.now() without a timezone is compared against a UTC timestamp from the JWT token. On servers not in UTC, this causes valid tokens to be considered expired.",
            "fix": "Use datetime.now(timezone.utc)",
            "also_found": ["auth/session.py:89"],
            "confidence": 96,
            "fix_diff": "- if datetime.now().timestamp() > token_payload[\"exp\"]:\n+ if datetime.now(timezone.utc).timestamp() > token_payload[\"exp\"]:"
         }
    else:
         analyzer = Analyzer(api_key=api_key)
         try:
             # In a real tool, we might want a spinner here
             with console.status("[bold green]Analyzing with Claude AI..."):
                analysis = analyzer.analyze(
                    spike=spike,
                    commit=commit_info,
                    top_error_message=top_message,
                    source_context=source_context,
                    git_context=git_context
                )
         except Exception as e:
              console.print(f"[red]Error analyzing with Claude: {e}[/red]")
              raise typer.Exit(1)

    # 6. Display
    Display.show_analysis(spike, commit_info, analysis, len(events), unique_types)

    # 7. Auto-fix prompt
    if auto_prompt_fix and analysis.get("fix_diff"):
        if Confirm.ask("Apply fix automatically?"):
            patcher = Patcher()
            if patcher.apply_diff(analysis["fix_diff"]):
                console.print("[green]Fix applied successfully.[/green]")
            else:
                 console.print("[red]Failed to apply fix. You may need to apply it manually.[/red]")


if __name__ == "__main__":
    app()
