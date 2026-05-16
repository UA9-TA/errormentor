import os
import subprocess

class ContextBuilder:
    def __init__(self, context_lines: int = 30):
        self.context_lines = context_lines

    def build_source_context(self, locations: list[dict]) -> str:
        """Reads surrounding lines for given file locations."""
        if not locations:
            return "No source locations found in traceback."

        context = []
        for loc in locations:
            file_path = loc['file']
            target_line = loc['line']

            if not os.path.isfile(file_path):
                # Try relative to repo root
                if os.path.isfile(os.path.join(os.getcwd(), file_path)):
                    file_path = os.path.join(os.getcwd(), file_path)
                else:
                    context.append(f"File not found: {file_path}")
                    continue

            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()

                start = max(0, target_line - self.context_lines - 1)
                end = min(len(lines), target_line + self.context_lines)

                snippet = [f"--- {file_path} ---"]
                for i in range(start, end):
                    prefix = ">> " if i == target_line - 1 else "   "
                    snippet.append(f"{i + 1:4d} {prefix}{lines[i].rstrip()}")

                context.append('\n'.join(snippet))
            except Exception as e:
                context.append(f"Error reading {file_path}: {e}")

        return '\n\n'.join(context)

    def build_git_context(self, files_touched: list[str]) -> str:
        """Gets recent git changes for the touched files."""
        if not files_touched:
            return "No files touched."

        context = []
        for f in files_touched:
            try:
                # Get the last 5 commits that touched this file to see recent changes
                result = subprocess.run(
                    ['git', 'log', '-n5', '-p', '--', f],
                    capture_output=True, text=True, check=True
                )
                if result.stdout:
                    context.append(f"Recent changes to {f}:\n{result.stdout.strip()}")
            except subprocess.CalledProcessError:
                context.append(f"Could not get git history for {f}")
            except FileNotFoundError:
                 context.append(f"git command not found")
                 break

        return '\n\n'.join(context)
