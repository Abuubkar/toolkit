from __future__ import annotations

import os
import uuid
from pathlib import Path


def write_github_output(name: str, value: str) -> bool:
    """Returns False (no-op) when GITHUB_OUTPUT isn't set. Uses a random
    delimiter (heredoc-style) so multiline values are written safely.
    """
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return False

    delimiter = f"ghadelim_{uuid.uuid4().hex}"
    with Path(output_path).open("a", encoding="utf-8") as f:
        f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
    return True
