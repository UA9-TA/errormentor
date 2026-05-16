import os
import subprocess

class Patcher:
    def apply_diff(self, diff_text: str) -> bool:
        """Applies a unified diff."""
        if not diff_text:
            return False

        # Write diff to temp file
        patch_file = "temp_fix.patch"
        with open(patch_file, "w") as f:
            f.write(diff_text)

        try:
            # Try using git apply first
            result = subprocess.run(["git", "apply", patch_file], capture_output=True, text=True)
            if result.returncode == 0:
                return True

            # Fallback to patch utility
            result = subprocess.run(["patch", "-p1", "-i", patch_file], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
             return False
        finally:
            if os.path.exists(patch_file):
                os.remove(patch_file)
