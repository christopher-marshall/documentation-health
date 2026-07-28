"""Example config for github.com/fastapi/fastapi.

Clone the repo first: git clone https://github.com/fastapi/fastapi
"""
import re

CONFIG = {
    "docs_glob": "docs/en/docs",
    # TODO: unverified. FastAPI uses gitmoji-style commits (its own vocabulary,
    # not dprint/prettier). This hasn't had the same investigation Polars got -
    # e.g. newsletter.md's last commit ("Update docs setup with latest configs
    # and plugins") looks like the same class of tooling-touch problem and isn't
    # caught by this yet. Check last_update_commit_msg across pages before
    # trusting days_since_update for this repo.
    "noise_commit_re": re.compile(r"\b(chore|lint(?:ing)?|formatting)\b", re.IGNORECASE),
    # FastAPI mixes two snippet conventions across its own docs: a fenced
    # ```Python block wrapping a {!path/to/file.py!} include, and a bare
    # {* path/to/file.py hl[...] *} macro with no fence at all.
    "example_patterns": [re.compile(r"\{\*.*?\*\}", re.DOTALL), re.compile(r"\{!.*?!\}", re.DOTALL)],
    # FastAPI's fenced examples have no rendered-output "rerun" twin - every
    # fenced block is its own distinct example.
    "fence_mode": "plain",
}
