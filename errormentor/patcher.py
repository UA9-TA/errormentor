import os
import subprocess

from errormentor.display import console


class Patcher:
    def apply_fix(self, fix_diff: str):
        if not fix_diff:
            console.print("No diff provided to apply.")
            return

        patch_file = "errormentor_fix.patch"
        with open(patch_file, "w") as f:
            f.write(fix_diff)

        try:
            # Try to apply patch
            result = subprocess.run(["git", "apply", patch_file], capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]Fix applied successfully![/green]")
            else:
                console.print(f"[red]Failed to apply fix automatically:[/red]\n{result.stderr}")
        finally:
            if os.path.exists(patch_file):
                os.remove(patch_file)
