# documentation-health

Per-page documentation health metrics for any docs-as-code project (docs stored
as Markdown/MDX in the repo, so git history maps cleanly to doc pages).

For each Markdown page under a docs directory, it computes:

| Metric | What it captures |
|---|---|
| `days_since_update` / `days_since_update_raw` | Staleness, with (`_raw` without) tooling/formatting commits filtered out |
| `age_days` | Days since the page's first commit |
| `commit_count`, `author_count` | Churn and bus-factor |
| `last_update_commit_msg` | The commit driving `days_since_update`, so you can eyeball whether it's real content work |
| `word_count`, `flesch_reading_ease` | Thin/bloated, dense/readable |
| `code_block_density` | Worked examples per 1000 words |
| `heading_count`, `heading_max_depth` | Structural completeness |
| `todo_flag` | Self-declared incompleteness (TODO/WIP/"coming soon") |
| `internal_link_count` | Connectedness in the doc set |

It does **not** compute a Diátaxis type (tutorial/how-to/reference/explanation)
or a composite health score - the former is an editorial judgment call, the
latter is a weighting decision only you can defend for your own use case. See
`examples/run_polars_example.py` for a pattern to layer both on top.

## Install

```
pip install -r requirements.txt
```

## Usage

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

## Writing a config for a new repo

Every docs-as-code project has its own build-tooling quirks. Two things in
particular don't generalize by default and need a quick look at the target
repo before you trust the output:

**`noise_commit_re`** - repo-wide formatting/tooling commits (a linter config
change, a mass reformat) touch many unrelated doc pages in one commit with no
real content edit. Left unfiltered, they make every page they touch look
falsely "fresh." Find these by sorting pages by `days_since_update` and reading
`last_update_commit_msg` for the ones that all show the same value - if several
unrelated pages share one commit, check what it actually did (`git show --stat
<hash>`) and add its keyword to the regex if it's noise.

**`example_patterns` / `fence_mode`** - how a project embeds worked code
examples varies a lot: a template macro that pulls source from an external
file, a bare include directive with no ` ``` ` fence around it at all, or a
fence immediately followed by a second fence that just re-renders the same
code's rendered output (in which case that second fence would double-count the
same example - `fence_mode="paired"` excludes it; `fence_mode="plain"` treats
every fence as its own example). Check a sample page's raw source before
assuming either.

`examples/polars_config.py` and `examples/fastapi_config.py` are two worked
configs showing how differently these can turn out even between two fairly
similar Python projects - including one open TODO (FastAPI's noise-commit
pattern) that hasn't been verified against real history yet.

## What generalizes and what doesn't

Tested against Polars and FastAPI's docs. The git-log-based metrics (staleness,
churn, authorship) and the structural text metrics (word count, heading depth,
TODO/link detection) ported cleanly across both. Anything tied to a project's
specific markdown/build conventions - code-example syntax, noise-commit
vocabulary - did not; each new repo needs its own config, not a shared
assumption.

## License

MIT - see [LICENSE](LICENSE).
