"""Install Playwright Chromium into a directory Vercel can bundle."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BROWSER_DIR = PROJECT_ROOT / ".playwright"


def main() -> None:
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_DIR)
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        cwd=PROJECT_ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
