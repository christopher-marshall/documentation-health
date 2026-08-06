"""Best-guess Diátaxis type (tutorial / how-to / reference / explanation) for
every page in the docs directory, derived from title/lead-in text keywords.

This is intended only as a starting point and will require careful manual review.

Usage:
    python suggest_diataxis.py path/to/cloned/repo docs/source/user-guide out.csv
"""
import csv
import re
from pathlib import Path

from dochealth.core import HEADING_ANCHOR_RE, TITLE_RE, to_prose

TUTORIAL_HINTS = re.compile(r"\b(getting started|quickstart|quick start|your first|introduction to|tutorial)\b", re.IGNORECASE)
HOWTO_HINTS = re.compile(r"^(how to|installing?|configuring|deploying|migrating|upgrading|setting up|using)\b", re.IGNORECASE)
REFERENCE_HINTS = re.compile(r"\b(api reference|reference|cli reference|configuration options|specification|schema)\b", re.IGNORECASE)
EXPLANATION_HINTS = re.compile(r"\b(understanding|why|concept|overview|architecture|comparison|background|design)\b", re.IGNORECASE)

# Page directory is usually more reliable than page title. Only fires on an exact segment match.
PATH_SEGMENT_HINTS = {
    "tutorial": "tutorial", "tutorials": "tutorial", "getting-started": "tutorial",
    "how-to": "how-to", "howto": "how-to", "guides": "how-to", "how-to-guides": "how-to",
    "reference": "reference", "api": "reference", "api-reference": "reference",
    "explanation": "explanation", "explanations": "explanation", "concepts": "explanation",
}


def suggest_type(path: str, title: str, prose: str) -> str:
    path_segments = {part.lower() for part in Path(path).parent.parts}
    for segment in path_segments:
        if segment in PATH_SEGMENT_HINTS:
            return PATH_SEGMENT_HINTS[segment]

    for text in (title or "", prose[:500]):
        if TUTORIAL_HINTS.search(text):
            return "tutorial"
        if HOWTO_HINTS.search(text):
            return "how-to"
        if REFERENCE_HINTS.search(text):
            return "reference"
        if EXPLANATION_HINTS.search(text):
            return "explanation"
    return "explanation"  # most common default for conceptual/user-guide content


def suggest_diataxis_csv(repo_path: Path, docs_glob: str, out_path: Path) -> None:
    docs = list((repo_path / docs_glob).rglob("*.md"))
    rows = []
    for f in docs:
        text = f.read_text(encoding="utf-8")
        prose = to_prose(text)
        title_match = TITLE_RE.search(prose)
        title = HEADING_ANCHOR_RE.sub("", title_match.group(1).strip()) if title_match else ""
        rel_path = str(f.relative_to(repo_path))
        rows.append({
            "path": rel_path,
            "diataxis_type": suggest_type(rel_path, title, prose),
        })

    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "diataxis_type"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo_path", type=Path)
    parser.add_argument("docs_glob")
    parser.add_argument("out_csv", type=Path)
    args = parser.parse_args()

    suggest_diataxis_csv(args.repo_path, args.docs_glob, args.out_csv)
    print(f"Wrote draft labels to {args.out_csv} - review and correct before using.")
