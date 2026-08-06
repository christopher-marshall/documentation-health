# Ideas & open threads

Things discussed while building this project that aren't implemented yet.
Not a roadmap - a reference so nothing raised in conversation gets lost. Check
each against the current code before acting on it; this file doesn't get
updated automatically as things change.

## Analysis layer (from the original capstone brief)

- **Composite health score + "fix these first" ranked list.** The brief's
  deliverable #2: a transparent weighted rank across the normalized metrics
  (staleness, thinness, readability, etc.), defensible in a writeup rather than
  a black box. This is what would turn the per-page metrics table into an
  actual prioritized action list. The README currently punts this to the user
  ("apply and calculate based on your own use case") - nothing scores or ranks
  pages yet.
- **Staleness-vs-code-churn cross-check.** Also from the brief: a stale page
  for stable, unchanging code is fine; a stale page for code that's under
  heavy active development is the real risk. Right now `days_since_update` is
  read in isolation, with no signal about how much the underlying code it
  documents has moved. Would need a second git-log pass over the *code*
  directories (not just docs) and some way to associate a doc page with the
  code it covers - the association step is the hard part, and hasn't been
  scoped out at all yet.

## Config authoring tooling

- **A `dochealth init <repo>` / config-generator command.** Right now writing
  a config for a new repo means copying `examples/polars_config.py` or
  `fastapi_config.py` and hand-editing it, then manually sorting the full
  `extract_docs()` output by `days_since_update` and eyeballing
  `last_update_commit_msg` to find noise-commit candidates (the README's
  current "how to find these" instructions). A generator script could:
  auto-guess `docs_glob` by finding the directory with the most `.md` files,
  scaffold a starter `config.py` from a template, and - reusing the
  `git --numstat` machinery already in `core.py`'s `_file_history()` - print a
  ranked report of commits touching many files *with real line changes* (the
  cosmetic-formatting candidates that still need a keyword; pure renames are
  already filtered automatically and wouldn't need to show up at all). Still
  an assistant, not full automation - `example_patterns`/`fence_mode` are
  genuinely project-specific and can't be reliably auto-detected.
- **FastAPI's `noise_commit_re` is still unverified against real history** -
  flagged directly in `examples/fastapi_config.py`'s own comment. FastAPI uses
  gitmoji-style commits, a different vocabulary than Polars' dprint/prettier
  pattern, and it hasn't had the same investigation pass (sort by
  `days_since_update`, check `git show --stat` on shared commits) that found
  Polars' noise commits. The comment calls out `newsletter.md`'s last commit
  ("Update docs setup with latest configs and plugins") as a likely example
  that isn't caught yet. Worth noting: the automatic pure-rename filter added
  to `core.py` may have already quietly fixed part of whatever this would have
  caught - re-verify before assuming the gap is as big as the comment
  describes.

## Dashboard

- **`app.py`'s own three TODO comments were never built into `app.py` itself**
  - Diátaxis coverage (counts + staleness by type), a readability-vs-length
  scatter, and a written narrative summary panel. All three *were* built, but
  only in `app-alt.py` - which was explicitly framed as a side-by-side
  comparison build, not a replacement. Open decision, not yet made: merge
  `app-alt.py`'s completed pieces back into the canonical `app.py`, keep both
  permanently as two different structural takes, or pick one as canonical and
  retire the other.

## Explicitly out of scope (context, not open items)

These came up in conversation but were deliberately decided against - listed
here only so they don't get re-proposed as if they were still open:

- **MySQL persistence** (`doc-health-project/extraction-test.ipynb` wrote
  `extract_docs()` output to a MySQL table). Confirmed dropped by the user.
- **Q2: GitHub Issues → doc-gap coverage correlation.** Scoped in the original
  brief as optional with an explicit "cut it if messy" fallback - looks like
  that fallback is exactly what happened.
