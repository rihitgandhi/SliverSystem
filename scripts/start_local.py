"""Run the website and checker API locally: python scripts/start_local.py."""

import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
local_dependencies = PROJECT_ROOT / '.codex_deps'
if local_dependencies.is_dir():
    sys.path.insert(0, str(local_dependencies))
os.chdir(PROJECT_ROOT)

from app import app


if __name__ == '__main__':
    print('AccessAI Checker: http://127.0.0.1:5000/checker.html', flush=True)
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
