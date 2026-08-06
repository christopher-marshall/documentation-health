# Documentation health dashboard

Per-page documentation health metrics for any docs-as-code project that uses
Markdown files.

DocHealth generates the following metrics for each page of documentation:

| Metric | What it captures |
|---|---|
| `days_since_update` / `days_since_update_raw` | Staleness with no-op renames and tooling/formatting commits filtered out. `_raw` includes all commits. |
| `age_days` | Days since the first commit |
| `commit_count`, `author_count` | Churn and bus-factor |
| `last_update_commit_msg` | The commit behind `days_since_update`. |
| `word_count`, `flesch_reading_ease` | Page length and readability. |
| `code_block_density` | Code blocks per 1000 words. |
| `heading_count`, `heading_max_depth` | Structural density and complexity. |
| `todo_flag` | Incompleteness (TODO/WIP/"coming soon") |
| `internal_link_count` | Measure of interconnectedness. |

Diátaxis type (tutorial/how-to/reference/explanation) and composite health
score are not automatically generated. Apply and calculate based on your own
use case. See `examples/run_polars_example.py` for an example.

## Install

```
pip install -r requirements.txt
```

## Use

```python
from pathlib import Path
from doc_health import extract_docs

config = {
    "docs_glob": "docs/source/user-guide",   # path under the repo to search for *.md
    "noise_commit_re": ...,                  # compiled regex matched against commit subjects
    "example_patterns": [...],               # compiled regexes for this project's snippet-include syntax
    "fence_mode": "paired",                  # or "plain" - see below
}

df = extract_docs(Path("path/to/cloned/repo"), config)
```

## Write a config for a new repo

Not everything generalises between documentation sets. Review your target docs
and adjust the following configuration options manually:

* **`noise_commit_re`**:
    * Two kinds of commit can make a page look falsely "fresh" without a real
      content edit: a pure rename/move (a directory reshuffle) and a
      repo-wide formatting/tooling pass (a linter config change, a mass
      reformat). `extract_docs()` drops the first kind automatically - it
      reads `git log --numstat` per file and excludes any commit with zero
      net line changes for that file, no config needed. `noise_commit_re`
      only needs to cover the second kind: commits that *did* change lines,
      but only cosmetically.
    * Find noisy commits by sorting pages by `days_since_update` and reading
      `last_update_commit_msg` for the ones that all show the same value. If
      several unrelated pages share one commit, check what it actually did
      (`git show --stat <hash>`) - if it's a pure rename you don't need to do
      anything, that's already handled; if it's a real-but-cosmetic edit
      (formatting, linting), add its keyword to the regex.
* **`example_patterns` / `fence_mode`**:
    * How a project embeds worked code examples varies a lot: a template macro
      that pulls source from an external file, a bare include directive with
      no ` ``` ` fence around it at all, or a fence immediately followed by a
      second fence that just re-renders the same code's rendered output (in
      which case that second fence would double-count the same example).
    * `fence_mode="paired"`: exclude output code blocks.
    * `fence_mode="plain"`: treat every fence as its own example.

`examples/polars_config.py` and `examples/fastapi_config.py` are two worked
configs showing how differently these can turn out even between two fairly
similar Python projects - including one open TODO (FastAPI's noise-commit
pattern) that hasn't been verified against real history yet.

## What generalizes and what doesn't

Tested against Polars and FastAPI's docs. The git-log-based metrics
(staleness, churn, authorship) and the structural text metrics (word count,
heading depth, TODO/link detection) ported cleanly across both. Anything tied
to a project's specific markdown/build conventions (code-example syntax,
noise-commit vocabulary) did not.

## License

MIT - see [LICENSE](LICENSE).
