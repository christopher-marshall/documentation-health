"""Example config for github.com/pola-rs/polars.

Clone the repo first: git clone https://github.com/pola-rs/polars
"""
import re

CONFIG = {
    "docs_glob": "docs/source/user-guide",
    # Polars formats docs with dprint; a repo-wide dprint config change touches
    # every doc file in one commit without any real content edit - confirmed by
    # checking last_update_commit_msg on affected pages (e.g. "docs: Change
    # dprint config (#19747)" was the top commit for ~8 unrelated pages at once).
    "noise_commit_re": re.compile(r"\b(dprint|prettier|black|isort|gofmt|chore|lint(?:ing)?|formatting)\b", re.IGNORECASE),
    # Polars pairs every real code example with an `exec="on"` fence that just
    # re-renders the same code's output - fence_mode="paired" counts only the real half.
    "example_patterns": [re.compile(r"\{\{\s*code_block\(")],
    "fence_mode": "paired",
}
