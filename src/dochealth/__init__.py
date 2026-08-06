"""dochealth - per-page documentation health metrics for docs-as-code repos.

    from pathlib import Path
    from dochealth import extract_docs

    df = extract_docs(Path("path/to/cloned/repo"), config)

See README.md for the config dict shape, or run `dochealth extract --help`
for the CLI.
"""
from .core import extract_docs

__all__ = ["extract_docs"]
