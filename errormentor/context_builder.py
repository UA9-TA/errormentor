import os
import subprocess


class ContextBuilder:
    def build(self, file_locations: list[dict], files_touched: list[str]) -> dict:
        context = {
            "source_context": {},
            "git_context": {}
        }

        # If we don't have file locations from traceback, use the files touched by commit
        files_to_check = files_touched
        for loc in file_locations:
            if "file" in loc and loc["file"] not in files_to_check:
                files_to_check.append(loc["file"])

        for filepath in files_to_check:
            # 1. Source context
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # If we have specific lines, get around them. Otherwise get whole file or truncated
                # For simplicity, if no line specified, get first 100 lines
                specific_lines = [loc.get("line") for loc in file_locations if loc.get("file") == filepath and loc.get("line")]

                if specific_lines:
                    # Get ±30 lines around first error line
                    target_line = specific_lines[0]
                    start = max(0, target_line - 31)
                    end = min(len(lines), target_line + 30)
                    context["source_context"][filepath] = "".join(lines[start:end])
                else:
                    context["source_context"][filepath] = "".join(lines[:100])
            else:
                context["source_context"][filepath] = "File not found locally"

            # 2. Git context
            try:
                # get recent git diff for those files (git log -n5 -p -- {file})
                result = subprocess.run(
                    ["git", "log", "-n5", "-p", "--", filepath],
                    capture_output=True,
                    text=True,
                    check=True
                )
                context["git_context"][filepath] = result.stdout
            except subprocess.CalledProcessError:
                context["git_context"][filepath] = "Failed to get git context"

        return context
