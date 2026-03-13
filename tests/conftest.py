from __future__ import annotations

import sys
from pathlib import Path

# Keep the repository root importable when tests run without an editable install.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
