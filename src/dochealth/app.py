"""Streamlit dashboard for documentation health metrics.

Starting-point scaffold — a working KPI row, staleness + bus-factor tables, and
sidebar filters over extract_docs() output. Build the rest (charts, Diátaxis
coverage, the written narrative panel) on top of this.

Run:
    dochealth dashboard [metrics.csv]      # preferred - installs with the package
    streamlit run src/dochealth/app.py     # or directly, from a checkout of this repo

Data source (pick in the sidebar):
  1. Sample data  — synthetic rows so the app renders with zero setup (default).
  2. Metrics CSV  — a file you saved earlier with extract_docs(...).to_csv("metrics.csv").
                    Preloaded automatically if you ran `dochealth dashboard metrics.csv`.
  3. Live extract — point at a cloned repo + a config module (e.g. examples/polars_config.py);
                    runs extract_docs() directly. Slower (one git call per page), cached per run.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Documentation Health", layout="wide")

# `dochealth dashboard metrics.csv` launches this via `streamlit run ... -- metrics.csv`,
# which Streamlit forwards straight into sys.argv - so this is set only when the CLI
# passed a CSV, never when running `streamlit run app.py` directly.
_cli_csv = sys.argv[1] if len(sys.argv) > 1 else None

# Columns extract_docs() produces, so the sample and the real thing share a shape.
METRIC_COLS = [
    "path", "title", "days_since_update", "days_since_update_raw",
    "last_update_commit_msg", "age_days", "commit_count", "author_count",
    "word_count", "flesch_reading_ease", "code_block_density",
    "heading_count", "heading_max_depth", "todo_flag", "internal_link_count",
]


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data
def run_extract(repo_path: str, config_module: str, diataxis_csv: str | None) -> pd.DataFrame:
    """Import a config module by path, run extract_docs(), optionally merge Diátaxis labels."""
    from dochealth import extract_docs  # imported here so the app still starts if deps are missing

    spec = importlib.util.spec_from_file_location("_dochealth_config", config_module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    df = extract_docs(Path(repo_path), module.CONFIG)
    if diataxis_csv and Path(diataxis_csv).exists():
        df = df.merge(pd.read_csv(diataxis_csv), on="path", how="left")
    return df


@st.cache_data
def sample_data(n: int = 45) -> pd.DataFrame:
    """Synthetic metrics so the dashboard renders before you wire in real data."""
    rng = np.random.default_rng(7)
    sections = ["getting-started", "how-to", "reference", "concepts"]
    dia = {"getting-started": "tutorial", "how-to": "how-to",
           "reference": "reference", "concepts": "explanation"}
    rows = []
    for i in range(n):
        section = rng.choice(sections)
        wc = int(rng.integers(0, 2500))
        rows.append({
            "path": f"docs/{section}/page_{i:02d}.md",
            "title": f"{section.replace('-', ' ').title()} page {i}",
            "days_since_update": int(rng.integers(2, 900)),
            "days_since_update_raw": int(rng.integers(2, 900)),
            "last_update_commit_msg": rng.choice(
                ["Fix typo", "Add example", "Restructure section", "Update for v2 API"]),
            "age_days": int(rng.integers(30, 1500)),
            "commit_count": int(rng.integers(1, 40)),
            "author_count": int(rng.integers(1, 6)),
            "word_count": wc,
            "flesch_reading_ease": round(float(rng.uniform(20, 75)), 1) if wc else None,
            "code_block_density": round(float(rng.uniform(0, 30)), 1) if wc else 0,
            "heading_count": int(rng.integers(1, 18)),
            "heading_max_depth": int(rng.integers(1, 5)),
            "todo_flag": bool(rng.random() < 0.15),
            "internal_link_count": int(rng.integers(0, 25)),
            "diataxis_type": dia[section],
        })
    return pd.DataFrame(rows)


def section_of(path: str) -> str:
    """Immediate parent folder of a page — a rough 'which part of the docs' grouping."""
    parts = Path(path).parent.parts
    return parts[-1] if parts else "(root)"


# --------------------------------------------------------------------------- #
# Sidebar: data source + filters
# --------------------------------------------------------------------------- #
st.sidebar.title("Documentation Health")
sources = ["Sample data", "Metrics CSV", "Live extract"]
source = st.sidebar.radio("Data source", sources, index=sources.index("Metrics CSV") if _cli_csv else 0)

if source == "Metrics CSV":
    csv_path = st.sidebar.text_input("Path to metrics CSV", _cli_csv or "metrics.csv")
    df = load_csv(csv_path) if csv_path and Path(csv_path).exists() else pd.DataFrame()
    if df.empty:
        st.warning(f"No CSV found at `{csv_path}`. Save one with "
                   "`extract_docs(...).to_csv('metrics.csv', index=False)`, or with "
                   "`dochealth extract <repo> --config <config.py> --out metrics.csv`.")
        st.stop()
elif source == "Live extract":
    repo_path = st.sidebar.text_input("Cloned repo path", "polars")
    config_module = st.sidebar.text_input("Config module", "examples/polars_config.py")
    diataxis_csv = st.sidebar.text_input("Diátaxis CSV (optional)", "examples/polars_diataxis_types.csv")
    if not (Path(repo_path).exists() and Path(config_module).exists()):
        st.warning("Set a valid repo path and config module in the sidebar to run a live extract.")
        st.stop()
    df = run_extract(repo_path, config_module, diataxis_csv or None)
else:
    df = sample_data()
    st.sidebar.caption("Showing synthetic sample data. Switch source to load your own.")

if df.empty:
    st.info("No pages found for this data source.")
    st.stop()

# Derived helper column used by the directory filter.
df = df.copy()
df["section"] = df["path"].map(section_of)

st.sidebar.divider()
st.sidebar.subheader("Filters")

# Staleness threshold — drives the KPI count and the ⚠ flag in the staleness table.
max_stale = int(df["days_since_update"].max())
stale_threshold = st.sidebar.slider("Stale after (days)", 30, max(90, max_stale), min(180, max_stale))

# Staleness range.
lo, hi = st.sidebar.slider("Staleness range (days)", 0, max_stale, (0, max_stale))

# Directory filter (empty = all).
sections = sorted(df["section"].unique())
picked_sections = st.sidebar.multiselect("Directory", sections, default=[])

# Diátaxis filter, only if the column is present (empty = all).
picked_types = []
if "diataxis_type" in df.columns:
    types = sorted(df["diataxis_type"].dropna().unique())
    picked_types = st.sidebar.multiselect("Diátaxis type", types, default=[])

# Free-text path filter — handy for a writer scanning one area.
path_query = st.sidebar.text_input("Path contains", "")

# Apply filters.
mask = df["days_since_update"].between(lo, hi)
if picked_sections:
    mask &= df["section"].isin(picked_sections)
if picked_types:
    mask &= df["diataxis_type"].isin(picked_types)
if path_query:
    mask &= df["path"].str.contains(path_query, case=False, na=False)
fdf = df[mask]

# --------------------------------------------------------------------------- #
# Header + KPI row
# --------------------------------------------------------------------------- #
st.title("Documentation Health Dashboard")
st.caption(f"{len(fdf)} of {len(df)} pages shown · staleness threshold {stale_threshold} days")

stale_pages = int((fdf["days_since_update"] > stale_threshold).sum())
single_author = int((fdf["author_count"] == 1).sum())
todo_pages = int(fdf["todo_flag"].sum()) if "todo_flag" in fdf.columns else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Pages", len(fdf))
k2.metric("Median staleness (days)", int(fdf["days_since_update"].median()))
k3.metric(f"Stale (> {stale_threshold}d)", stale_pages,
          delta=f"{stale_pages / len(fdf):.0%}" if len(fdf) else None, delta_color="inverse")
k4.metric("Single-author pages", single_author, help="Bus-factor risk: only one author has touched the page.")
median_read = fdf["flesch_reading_ease"].median()
k5.metric("Median readability", f"{median_read:.0f}" if pd.notna(median_read) else "—",
          help="Flesch reading ease (higher = easier). Pages with no prose are excluded.")

st.divider()

# --------------------------------------------------------------------------- #
# Staleness + bus-factor tables
# --------------------------------------------------------------------------- #
left, right = st.columns(2)

with left:
    st.subheader("Stalest pages")
    stale = fdf.sort_values("days_since_update", ascending=False).copy()
    stale["flag"] = np.where(stale["days_since_update"] > stale_threshold, "⚠", "")
    st.dataframe(
        stale[["flag", "path", "days_since_update", "author_count", "last_update_commit_msg"]],
        hide_index=True, use_container_width=True,
        column_config={
            "flag": st.column_config.TextColumn("", width="small"),
            "path": st.column_config.TextColumn("Page"),
            "days_since_update": st.column_config.NumberColumn("Stale (days)"),
            "author_count": st.column_config.NumberColumn("Authors"),
            "last_update_commit_msg": st.column_config.TextColumn("Last commit"),
        },
    )

with right:
    st.subheader("Bus-factor risk (single author)")
    # Biggest single-author pages first — most content resting on one person.
    solo = (fdf[fdf["author_count"] == 1]
            .sort_values("word_count", ascending=False))
    if solo.empty:
        st.success("No single-author pages in the current filter.")
    else:
        st.dataframe(
            solo[["path", "word_count", "days_since_update", "commit_count"]],
            hide_index=True, use_container_width=True,
            column_config={
                "path": st.column_config.TextColumn("Page"),
                "word_count": st.column_config.NumberColumn("Words"),
                "days_since_update": st.column_config.NumberColumn("Stale (days)"),
                "commit_count": st.column_config.NumberColumn("Commits"),
            },
        )

# --------------------------------------------------------------------------- #
# Build-on-this: next sections to add
# --------------------------------------------------------------------------- #
with st.expander("Full metrics table"):
    st.dataframe(fdf.drop(columns=["section"]), hide_index=True, use_container_width=True)

# TODO (next): Diátaxis coverage — counts per type + staleness by type (see the
#   notebook's countplot/boxplot). Only render when 'diataxis_type' is present.
# TODO (next): readability-vs-length scatter, coloured by Diátaxis type.
# TODO (next): a written narrative panel (st.markdown) that reads the numbers for a
#   stakeholder — the writer/analyst layer that makes this dashboard yours.
