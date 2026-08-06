"""Per-page documentation health metrics for a docs-as-code repo.

Git-log parsing, prose/word-count/heading/link/TODO metrics are the same across
any docs-as-code project and live here. Everything that varies by project - what
a "noise" commit looks like, how that project embeds code examples - is supplied
by the caller as a config dict (see examples/ for two worked configs) rather than
hardcoded here. Public entry point is extract_docs(); re-exported as
dochealth.extract_docs.
"""
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import textstat

TITLE_RE = re.compile(r"^#\s+(.+)", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{1,6})\s+.+", re.MULTILINE)
TODO_RE = re.compile(r"\b(TODO|WIP|coming soon)\b", re.IGNORECASE)
# Internal page links only: markdown links to a relative target. The (?<!!) drops
# image embeds (![alt](img.png)), and the lookahead drops external URLs, mailto:
# links, and same-page anchors (#section) - none of which are links to another page.
INTERNAL_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\((?!https?://|mailto:|#)[^)]+\)")
FENCE_LINE_RE = re.compile(r"^```(.*)$", re.MULTILINE)

# mkdocs-material attr_list permalink syntax, e.g. "# OAuth2 scopes { #oauth2-scopes }".
# Harmless to strip on projects that don't use it, so this runs unconditionally
# rather than living in per-repo config.
HEADING_ANCHOR_RE = re.compile(r"\s*\{:?\s*#[\w-]+[^}]*\}\s*$")


def to_prose(text: str) -> str:
    """Strip markup that isn't reader-visible prose, for word_count / readability only."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)    # fenced code blocks
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)  # {{ macro(...) }} templates
    text = re.sub(r"\{%.*?%\}", "", text, flags=re.DOTALL)    # {% ... %} jinja statements
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)   # HTML comments
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)  # markdown table rows - not narrative prose
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # markdown links: keep visible text, drop the URL
    text = re.sub(r"https?://\S+", "", text)                  # bare URLs
    text = re.sub(r"`([^`]*)`", r"\1", text)                  # inline code: drop backticks, keep the word
    return text


def strip_code(text: str) -> str:
    """Remove code (fenced + inline) but keep everything else - including HTML
    comments. Used for todo_flag: a TODO inside a documented code sample is the
    example's, not the writer's, while writers often park real TODO/WIP notes in
    HTML comments (which to_prose strips, so prose is the wrong source here).
    """
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # fenced code blocks
    text = re.sub(r"`[^`]*`", "", text)                     # inline code spans (drop contents too)
    return text


def count_examples(text: str, example_patterns: list[re.Pattern], fence_mode: str) -> int:
    """Count distinct worked examples on a page.

    example_patterns: project-specific snippet-include macros - e.g. a template
    macro that pulls source from an external file, or a bare include directive
    that isn't wrapped in a ``` fence at all.

    fence_mode:
      "paired" - every real fenced example is immediately followed by a rendered
                 "rerun" of the same code (some docs generators emit both) - count
                 only the real half, not the rerun.
      "plain"  - every fenced block is itself a distinct example, no rerun twin.
    """
    macro_count = sum(len(pattern.findall(text)) for pattern in example_patterns)
    fence_blocks = FENCE_LINE_RE.findall(text)[0::2]  # even indices = openers, odd = closers
    if fence_mode == "paired":
        fence_count = sum(1 for info in fence_blocks if 'exec="on"' not in info)
    else:
        fence_count = len(fence_blocks)
    return macro_count + fence_count


def _file_history(repo_path: Path, rel_path: str) -> list[tuple[str, str, str, int, int]]:
    """One row per commit touching this file: (date, author, subject, lines_added, lines_deleted).

    Line counts come from --numstat. A pure rename/move with identical content
    (e.g. a directory reshuffle) shows 0/0 - that's what tells it apart from a
    commit that actually edited the file, without needing to guess from the
    commit message.
    """
    out = subprocess.run(
        ["git", "-C", str(repo_path), "log", "--follow", "--numstat",
         "--format=COMMIT|%aI|%an|%s", "--", rel_path],
        capture_output=True, text=True).stdout.splitlines()

    commits = []
    date = author = subject = None
    added = deleted = 0
    for line in out:
        if line.startswith("COMMIT|"):
            if date is not None:
                commits.append((date, author, subject, added, deleted))
            _, date, author, subject = line.split("|", 3)
            added = deleted = 0
        elif line.strip():
            a_str, d_str, *_ = line.split("\t")
            # Binary files report "-" for both counts; treat as a real change
            # rather than guess it's a no-op rename.
            added += int(a_str) if a_str.isdigit() else 1
            deleted += int(d_str) if d_str.isdigit() else 1
    if date is not None:
        commits.append((date, author, subject, added, deleted))
    return commits


def extract_docs(repo_path: Path, config: dict) -> pd.DataFrame:
    """Build the per-page metrics table for one docs-as-code repo.

    config keys:
      docs_glob        - path under repo_path to search for *.md files, e.g. "docs".
      noise_commit_re   - compiled regex matched against commit subjects; commits
                          that match are excluded from staleness/churn/authorship
                          on top of the automatic pure-rename filter (see
                          _file_history) - this is for commits that DID change
                          lines but only cosmetically (a repo-wide reformat) -
                          see README for how to find these for a new repo.
      example_patterns  - list of compiled regexes, see count_examples().
      fence_mode        - "paired" or "plain", see count_examples().
    """
    docs = list((repo_path / config["docs_glob"]).rglob("*.md"))
    noise_commit_re = config["noise_commit_re"]
    example_patterns = config["example_patterns"]
    fence_mode = config["fence_mode"]

    rows = []
    for f in docs:
        commits = _file_history(repo_path, str(f.relative_to(repo_path)))
        if not commits:
            continue

        last_raw = datetime.fromisoformat(commits[0][0])

        content_commits = [
            (d, a, s) for d, a, s, added, deleted in commits
            if (added + deleted) > 0 and not noise_commit_re.search(s)
        ]
        if not content_commits:
            # Every commit was noise (rename and/or keyword) - fall back to raw log
            # rather than report no history at all for a file that does have some.
            content_commits = [(d, a, s) for d, a, s, _, _ in commits]

        dates, authors, subjects = zip(*content_commits)
        last, first = datetime.fromisoformat(dates[0]), datetime.fromisoformat(dates[-1])

        text = f.read_text(encoding="utf-8")
        prose = to_prose(text)
        word_count = len(prose.split())
        title_match = TITLE_RE.search(prose)
        title = HEADING_ANCHOR_RE.sub("", title_match.group(1).strip()) if title_match else None
        example_count = count_examples(text, example_patterns, fence_mode)
        heading_levels = [len(h) for h in HEADING_RE.findall(prose)]

        rows.append({
            "path": str(f.relative_to(repo_path)),
            "title": title,
            "days_since_update": (datetime.now(timezone.utc) - last).days,
            "days_since_update_raw": (datetime.now(timezone.utc) - last_raw).days,
            "last_update_commit_msg": subjects[0],
            "age_days": (datetime.now(timezone.utc) - first).days,
            "commit_count": len(content_commits),
            "author_count": len(set(authors)),
            "word_count": word_count,
            # None, not 0.0: textstat returns 0.0 for empty prose, which reads as
            # "extremely hard to read" rather than "no prose to score" (e.g. a pure
            # reference stub that is all table/code). None keeps it out of the stats.
            "flesch_reading_ease": textstat.flesch_reading_ease(prose) if word_count else None,
            "code_block_density": (example_count / word_count * 1000) if word_count else 0,
            "heading_count": len(heading_levels),
            "heading_max_depth": max(heading_levels) if heading_levels else 0,
            "todo_flag": bool(TODO_RE.search(strip_code(text))),
            "internal_link_count": len(INTERNAL_LINK_RE.findall(text)),
        })

    return pd.DataFrame(rows)
