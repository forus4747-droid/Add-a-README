"""Step 7 — set it running: all six skills, once, in exactly this order.

    1. capture   (watch the playlist)
    2. inbox     (pick up Telegram links)
    3. fetch     (get the actual text)
    4. sort      (group into subjects)
    5. build     (NotebookLM material — needs your own machine + notebooklm login)
    6. digest    (Telegram summary)

Each step finishes before the next starts. A step that fails stops the run
(rows park at "failed" with a reason, so nothing silently blocks the queue).
Schedule this daily at 6am — see the README.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["capture", "inbox", "fetch", "sort", "build", "digest"]


def main() -> None:
    only = sys.argv[1:] or STEPS
    for step in only:
        if step not in STEPS:
            sys.exit(f"Unknown step {step!r}. Steps, in order: {', '.join(STEPS)}")
        print(f"\n=== learning-{step} ===")
        result = subprocess.run([sys.executable, str(HERE / f"{step}.py")])
        if result.returncode != 0:
            sys.exit(f"Step '{step}' failed (exit {result.returncode}); stopping here.")
    print("\nAll steps finished.")


if __name__ == "__main__":
    main()
