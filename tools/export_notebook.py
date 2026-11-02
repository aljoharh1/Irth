"""Export the system code of Irth.ipynb into irth/system.py.

The notebook is the single source of truth. Every code cell that defines part
of the system is copied in notebook order; test cells and the cell that opens
the dashboard are left out (the tests are run from tests/ instead).

    python tools/export_notebook.py          # regenerate irth/system.py
    python tools/export_notebook.py --check  # exit 1 if it is out of date
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOK = os.path.join(ROOT, "Irth.ipynb")
TARGET = os.path.join(ROOT, "irth", "system.py")
SKIP = re.compile(r"test|start the live dashboard", re.IGNORECASE)

HEADER = '''"""Irth - multi-agent system for museum artifact protection.

AUTO-GENERATED from Irth.ipynb by tools/export_notebook.py - do not edit here;
edit the notebook and run the export again.
"""
# flake8: noqa
'''


def notebook_sections(path=NOTEBOOK):
    """Yield (heading, source) for every code cell, with its markdown heading."""
    with open(path, encoding="utf-8") as handle:
        cells = json.load(handle)["cells"]
    heading = ""
    for cell in cells:
        source = "".join(cell["source"])
        if cell["cell_type"] == "markdown":
            heading = source.strip().splitlines()[0].lstrip("#").strip() if source.strip() else ""
        else:
            yield heading, source


def build():
    parts = [HEADER]
    for heading, source in notebook_sections():
        if SKIP.search(heading):
            continue
        title = heading.replace("*", "")
        parts.append(f"\n\n# {'=' * 76}\n# {title}\n# {'=' * 76}\n\n{source.strip()}\n")
    return "".join(parts)


if __name__ == "__main__":
    text = build()
    if "--check" in sys.argv:
        with open(TARGET, encoding="utf-8") as handle:
            same = handle.read() == text
        print("irth/system.py is up to date" if same else "irth/system.py is OUT OF DATE")
        sys.exit(0 if same else 1)
    with open(TARGET, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"wrote {os.path.relpath(TARGET, ROOT)}")
