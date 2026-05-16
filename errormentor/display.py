from typing import Any

from rich.console import Console

from .git_correlator import CommitInfo
from .spike_detector import SpikeReport

console = Console()

class Display:
    @staticmethod
    def show_analysis(spike: SpikeReport, commit: CommitInfo, analysis: dict[str, Any], total_events: int, unique_types: int):
        console.print("ErrorMentor — Production Error Analysis", style="bold blue")
        console.print("──────────────────────────────────────────────────", style="dim")

        # Header
        console.print(f"✦ Errors analyzed     {total_events} log lines, {unique_types} unique error types")
        spike_time = spike.spike_started_at.strftime("%H:%M UTC")
        console.print(f"✦ Spike detected      {spike.error_type}  ↑ {int(spike.acceleration_factor * 100)}% at {spike_time}")
        console.print("")

        # Root Cause
        console.print("  ── Root Cause ────────────────────────────────────", style="dim")
        console.print(f"  [bold]Error[/bold]         {spike.error_type}: {analysis.get('root_cause', 'Unknown')}")
        console.print(f"  [bold]Location[/bold]      {analysis.get('location', 'Unknown')}")
        console.print(f"  [bold]Frequency[/bold]     {spike.baseline_rate}/min → {spike.peak_rate}/min (spike started {spike_time})")
        console.print("")

        # Git Correlation
        if commit:
            console.print("  ── Git Correlation ───────────────────────────────", style="dim")
            console.print("  Most likely commit:")
            commit_time = commit.timestamp.strftime("%H:%M UTC")
            console.print(f"  {commit.hash[:7]}  {commit_time}  {commit.message}")
            console.print(f"  Author: {commit.author}")
            console.print(f"  Files touched: {', '.join(commit.files_touched)}")
            console.print("")
            console.print(f"  Time delta: error spike began {commit.delta_seconds} seconds after deploy")
            console.print("")

        # AI Analysis
        console.print("  ── AI Analysis ───────────────────────────────────", style="dim")
        explanation = analysis.get("explanation", "").replace("\n", "\n                ")
        console.print(f"  [bold]Root cause[/bold]    {explanation}")
        console.print("")

        fix_text = analysis.get("fix", "").replace("\n", "\n                ")
        console.print(f"  [bold]Fix[/bold]           {analysis.get('location', '')}:")

        if diff := analysis.get('fix_diff'):
            for line in diff.split('\n'):
                if line.startswith('-'):
                    console.print(f"                [red]{line}[/red]")
                elif line.startswith('+'):
                    console.print(f"                [green]{line}[/green]")
                else:
                    console.print(f"                {line}")
        else:
             console.print(f"                {fix_text}")

        console.print("")

        if also_found := analysis.get("also_found"):
            console.print(f"  [bold]Also found[/bold]    {', '.join(also_found)}")
            console.print("")

        confidence = analysis.get("confidence", 0)
        console.print(f"  [bold]Confidence[/bold]    {confidence}%")
        console.print("──────────────────────────────────────────────────", style="dim")
