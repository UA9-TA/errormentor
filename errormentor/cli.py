from typing import Optional

import typer

from errormentor.analyzer import Analyzer
from errormentor.context_builder import ContextBuilder
from errormentor.display import Display
from errormentor.git_correlator import GitCorrelator
from errormentor.log_parser import LogParser
from errormentor.patcher import Patcher
from errormentor.spike_detector import SpikeDetector

app = typer.Typer(help="ErrorMentor — Production Error Analysis")

@app.command()
def analyze(
    file: str = typer.Argument(..., help="Path to log file to analyze"),
    correlate: bool = typer.Option(False, "--correlate", help="Correlate with recent git commits"),
    tail: bool = typer.Option(False, "--tail", help="Tail the log file (not implemented yet)"),
    datadog: Optional[str] = typer.Option(None, "--datadog", help="Datadog query (not implemented yet)"),
    since: Optional[str] = typer.Option(None, "--since", help="Time filter (not implemented yet)")
):
    """Analyze a log file or error stream."""
    parser = LogParser()
    detector = SpikeDetector()
    display = Display()

    try:
        events = parser.parse_file(file)
    except Exception as e:
        display.print_error(f"Failed to read log file: {e}")
        raise typer.Exit(1)

    if not events:
        display.print_error("No valid error events found in log.")
        raise typer.Exit(1)

    unique_types = len(set(e.error_type for e in events if e.error_type))
    spike_report = detector.detect(events)

    if not spike_report:
        display.print_error("No significant error spikes detected.")
        raise typer.Exit(0)

    # Get most common message for the spike error type
    spike_events = [e for e in events if e.error_type == spike_report.error_type]
    from collections import Counter
    msg_counts = Counter(e.message for e in spike_events)
    top_message = msg_counts.most_common(1)[0][0] if msg_counts else "Unknown error"

    commit = None
    delta_seconds = 0
    context = {"source_context": {}, "git_context": {}}

    if correlate:
        correlator = GitCorrelator()
        commits = correlator.get_commits_around(spike_report.spike_started_at)
        if commits:
            commit = commits[0]
            delta_seconds = int((spike_report.spike_started_at - commit.timestamp).total_seconds())

            # Extract file locations from events if possible, or just use touched files
            file_locations = []
            for e in spike_events:
                file_locations.extend(e.file_locations)

            ctx_builder = ContextBuilder()
            context = ctx_builder.build(file_locations, commit.files_touched.copy())

    analyzer = Analyzer()
    analysis_result = analyzer.analyze(spike_report, commit, delta_seconds, context, top_message)

    display.print_analysis(len(events), unique_types, spike_report, commit, analysis_result, delta_seconds)

    if analysis_result.get("fix_diff"):
        if typer.confirm("Apply fix automatically?"):
            patcher = Patcher()
            patcher.apply_fix(analysis_result["fix_diff"])

@app.command()
def diagnose(file: str = typer.Argument(..., help="Path to log file to diagnose")):
    """Show the diagnosis for a log file."""
    analyze(file=file, correlate=True)

@app.command()
def fix(file: str = typer.Argument(..., help="Path to log file to analyze and fix")):
    """Auto-generate a fix suggestion."""
    analyze(file=file, correlate=True)

if __name__ == "__main__":
    app()
