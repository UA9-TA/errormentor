from rich.console import Console

console = Console()

class Display:
    def print_analysis(self, num_logs: int, num_types: int, spike_report, commit, analysis_result, delta_seconds: int):
        console.print("ErrorMentor — Production Error Analysis", style="bold blue")
        console.print("─" * 50)

        console.print(f"✦ Errors analyzed     {num_logs} log lines, {num_types} unique error types")
        if spike_report:
            time_str = spike_report.spike_started_at.strftime("%H:%M UTC")
            pct = int((spike_report.acceleration_factor - 1) * 100)
            console.print(f"✦ Spike detected      {spike_report.error_type}  ↑ {pct}% at {time_str}")
        else:
            console.print("✦ Spike detected      None")
            return

        console.print("")
        console.print("  ── Root Cause ────────────────────────────────────", style="dim")
        console.print(f"  Error         {spike_report.error_type}")
        console.print(f"  Location      {analysis_result.get('location', 'unknown')}")
        console.print(f"  Frequency     {spike_report.baseline_rate:.1f}/min → {spike_report.peak_rate:.1f}/min (spike started {time_str})")

        console.print("")
        console.print("  ── Git Correlation ───────────────────────────────", style="dim")
        if commit:
            commit_time = commit.timestamp.strftime("%H:%M UTC")
            console.print("  Most likely commit:")
            console.print(f"  {commit.hash[:7]}  {commit_time}  {commit.message}")
            console.print(f"  Author: {commit.author}")
            console.print(f"  Files touched: {', '.join(commit.files_touched)}")
            console.print("")
            console.print(f"  Time delta: error spike began {delta_seconds} seconds after deploy")
        else:
            console.print("  No recent commits found within 10 minutes of spike.")

        console.print("")
        console.print("  ── AI Analysis ───────────────────────────────────", style="dim")
        console.print(f"  Root cause    {analysis_result.get('root_cause', '')}")
        console.print("")
        console.print(f"  Fix           {analysis_result.get('location', '')}:")
        fix_diff = analysis_result.get('fix_diff', '')
        if fix_diff:
            for line in fix_diff.split('\n'):
                if line.startswith('+'):
                    console.print(f"                [green]{line}[/green]")
                elif line.startswith('-'):
                    console.print(f"                [red]{line}[/red]")
                else:
                    console.print(f"                {line}")
        else:
            console.print(f"                {analysis_result.get('fix', '')}")

        if analysis_result.get('also_found'):
            console.print("")
            console.print(f"  Also found    {', '.join(analysis_result.get('also_found', []))}")

        console.print("")
        console.print(f"  Confidence    {analysis_result.get('confidence', 0)}%")
        console.print("─" * 50)

    def print_error(self, message: str):
        console.print(f"[red]Error:[/red] {message}")
