"""Streamlit dashboard for documentation health metrics — alt build.

Same data contract as app.py (extract_docs() output) but different structural
choices, built for side-by-side comparison:
  - tabbed layout instead of columns + expander
  - CSV via drag-drop upload instead of a typed path; config module picked
    from a dropdown over examples/*_config.py instead of typed free-text
  - completes the three "build on this" items app.py leaves as TODO:
    Diátaxis coverage charts, a readability-vs-length scatter, and an
    auto-written narrative panel that reads the numbers for a stakeholder

Charts follow this session's dataviz skill: single-hue magnitude bars (blue),
the fixed status pair (good/warning) for the todo-flag breakdown, faceted
small multiples instead of a 4-way categorical scatter (Diátaxis has 4 types,
over the palette's 3-slot all-pairs cap for scatter/bubble forms), hairline
recessive gridlines, and no dual axes.

Run (from a checkout of this repo - unlike app.py, this comparison build has no
CLI wrapper of its own):
    pip install -e ".[dashboard]"
    streamlit run app-alt.py

Data source (pick in the sidebar):
  1. Sample data  — synthetic rows so the app renders with zero setup (default).
  2. Upload CSV   — drag in a file you saved earlier with extract_docs(...).to_csv(...).
  3. Live extract — point at a cloned repo + pick a config module found under
                    examples/; runs extract_docs() directly, cached per run.
"""
import glob
import importlib.util
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Documentation Health (alt)", layout="wide")

# --------------------------------------------------------------------------- #
# Palette — see the dataviz skill's references/palette.md. Single-hue blue for
# magnitude bars/scatter, the fixed status pair for the todo-flag breakdown.
# --------------------------------------------------------------------------- #
MODE = "dark" if st.get_option("theme.base") == "dark" else "light"
BLUE = "#3987e5" if MODE == "dark" else "#2a78d6"
GOOD = "#0ca30c"
WARNING = "#fab219"
MUTED = "#898781"
GRID = "#2c2c2a" if MODE == "dark" else "#e1e0d9"
AXIS = "#383835" if MODE == "dark" else "#c3c2b7"


def styled(chart: alt.Chart) -> alt.Chart:
    """Recessive hairline gridlines/axes, muted axis text — shared across every chart."""
    return chart.configure_axis(
        grid=True, gridColor=GRID, gridDash=[1, 0], domainColor=AXIS,
        tickColor=AXIS, labelColor=MUTED, titleColor=MUTED,
    ).configure_view(strokeWidth=0)


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
@st.cache_data
def load_csv_bytes(raw: bytes) -> pd.DataFrame:
    import io
    return pd.read_csv(io.BytesIO(raw))


@st.cache_data
def run_extract(repo_path: str, config_module: str, diataxis_csv: str | None) -> pd.DataFrame:
    from dochealth import extract_docs  # imported here so the app still starts if deps are missing

    spec = importlib.util.spec_from_file_location("_dochealth_config_alt", config_module)
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
    parts = Path(path).parent.parts
    return parts[-1] if parts else "(root)"


# --------------------------------------------------------------------------- #
# Sidebar: data source + filters
# --------------------------------------------------------------------------- #
st.sidebar.title("Documentation Health — alt")
source = st.sidebar.radio("Data source", ["Sample data", "Upload CSV", "Live extract"])

if source == "Upload CSV":
    uploaded = st.sidebar.file_uploader("Metrics CSV", type="csv")
    if uploaded is None:
        st.info("Upload a CSV saved with `extract_docs(...).to_csv('metrics.csv', index=False)`.")
        st.stop()
    df = load_csv_bytes(uploaded.getvalue())
elif source == "Live extract":
    repo_path = st.sidebar.text_input("Cloned repo path", "polars")
    config_files = sorted(glob.glob("examples/*_config.py"))
    config_module = st.sidebar.selectbox("Config module", config_files) if config_files else None
    diataxis_csv = st.sidebar.text_input("Diátaxis CSV (optional)", "examples/polars_diataxis_types.csv")
    if not config_module or not Path(repo_path).exists():
        st.warning("Set a valid cloned-repo path and pick a config module in the sidebar.")
        st.stop()
    df = run_extract(repo_path, config_module, diataxis_csv or None)
else:
    df = sample_data()
    st.sidebar.caption("Showing synthetic sample data. Switch source to load your own.")

if df.empty:
    st.info("No pages found for this data source.")
    st.stop()

df = df.copy()
df["section"] = df["path"].map(section_of)

st.sidebar.divider()
st.sidebar.subheader("Filters")

max_stale = int(df["days_since_update"].max())
stale_threshold = st.sidebar.slider("Stale after (days)", 30, max(90, max_stale), min(180, max_stale))

sections = sorted(df["section"].unique())
picked_sections = st.sidebar.multiselect("Directory", sections, default=[])

picked_types = []
if "diataxis_type" in df.columns:
    types = sorted(df["diataxis_type"].dropna().unique())
    picked_types = st.sidebar.multiselect("Diátaxis type", types, default=[])

path_query = st.sidebar.text_input("Path contains", "")

mask = pd.Series(True, index=df.index)
if picked_sections:
    mask &= df["section"].isin(picked_sections)
if picked_types:
    mask &= df["diataxis_type"].isin(picked_types)
if path_query:
    mask &= df["path"].str.contains(path_query, case=False, na=False)
fdf = df[mask]

if fdf.empty:
    st.warning("No pages match the current filters.")
    st.stop()

# --------------------------------------------------------------------------- #
# Header + tabs
# --------------------------------------------------------------------------- #
st.title("Documentation Health Dashboard (alt)")
st.caption(f"{len(fdf)} of {len(df)} pages shown · staleness threshold {stale_threshold} days")

tab_overview, tab_staleness, tab_diataxis, tab_readability, tab_raw = st.tabs(
    ["Overview", "Staleness & authorship", "Diátaxis coverage", "Readability", "Raw data"]
)

# --------------------------------------------------------------------------- #
# Overview: KPIs + auto-written narrative
# --------------------------------------------------------------------------- #
with tab_overview:
    stale_pages = int((fdf["days_since_update"] > stale_threshold).sum())
    single_author = int((fdf["author_count"] == 1).sum())
    todo_pages = int(fdf["todo_flag"].sum()) if "todo_flag" in fdf.columns else 0
    median_stale = int(fdf["days_since_update"].median())
    median_read = fdf["flesch_reading_ease"].median()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Pages", len(fdf))
    k2.metric("Median staleness (days)", median_stale)
    k3.metric(f"Stale (> {stale_threshold}d)", stale_pages,
              delta=f"{stale_pages / len(fdf):.0%}", delta_color="inverse")
    k4.metric("Single-author pages", single_author, help="Bus-factor risk: only one author has touched the page.")
    k5.metric("Median readability", f"{median_read:.0f}" if pd.notna(median_read) else "—",
              help="Flesch reading ease (higher = easier). Pages with no prose are excluded.")

    st.divider()
    st.subheader("Summary")

    lines = [
        f"Of the **{len(fdf)}** pages in view, **{stale_pages}** ({stale_pages / len(fdf):.0%}) "
        f"haven't been meaningfully updated in over {stale_threshold} days, and the median page "
        f"was last touched **{median_stale} days** ago.",
        f"**{single_author}** page(s) ({single_author / len(fdf):.0%}) have had only one author — "
        "the content depends on a single person's availability to maintain.",
    ]
    if todo_pages:
        lines.append(f"**{todo_pages}** page(s) still carry a TODO/WIP/\"coming soon\" marker.")
    if "diataxis_type" in fdf.columns and fdf["diataxis_type"].notna().any():
        counts = fdf["diataxis_type"].value_counts()
        top_type, top_n = counts.index[0], counts.iloc[0]
        lines.append(
            f"Coverage skews toward **{top_type}** ({top_n} of {counts.sum()} classified pages) — "
            "see the Diátaxis coverage tab for the full split."
        )
    if pd.notna(median_read):
        read_label = "easy" if median_read >= 60 else "fairly technical" if median_read >= 30 else "dense"
        lines.append(f"Prose reads as **{read_label}** overall (median Flesch reading ease {median_read:.0f}).")

    st.markdown("\n\n".join(f"- {line}" for line in lines))

# --------------------------------------------------------------------------- #
# Staleness & authorship
# --------------------------------------------------------------------------- #
with tab_staleness:
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
        solo = fdf[fdf["author_count"] == 1].sort_values("word_count", ascending=False)
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

    st.subheader("Staleness distribution")
    hist = (
        alt.Chart(fdf)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=BLUE)
        .encode(
            x=alt.X("days_since_update:Q", bin=alt.Bin(maxbins=30), title="Days since update"),
            y=alt.Y("count():Q", title="Pages"),
            tooltip=[alt.Tooltip("count():Q", title="Pages")],
        )
        .properties(height=280)
    )
    st.altair_chart(styled(hist), use_container_width=True)

# --------------------------------------------------------------------------- #
# Diátaxis coverage
# --------------------------------------------------------------------------- #
with tab_diataxis:
    if "diataxis_type" not in fdf.columns or fdf["diataxis_type"].dropna().empty:
        st.info("No `diataxis_type` column in this data source — merge a Diátaxis CSV "
                 "(see `examples/polars_diataxis_types.csv`) to see coverage.")
    else:
        ddf = fdf.dropna(subset=["diataxis_type"])
        left, right = st.columns(2)

        with left:
            st.subheader("Pages per type")
            coverage = (
                alt.Chart(ddf)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=BLUE, size=24)
                .encode(
                    x=alt.X("diataxis_type:N", title=None, sort="-y"),
                    y=alt.Y("count():Q", title="Pages"),
                    tooltip=[alt.Tooltip("diataxis_type:N", title="Type"), alt.Tooltip("count():Q", title="Pages")],
                )
                .properties(height=280)
            )
            st.altair_chart(styled(coverage), use_container_width=True)

        with right:
            st.subheader("Median staleness by type")
            med_stale = ddf.groupby("diataxis_type", as_index=False)["days_since_update"].median()
            stale_by_type = (
                alt.Chart(med_stale)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=BLUE, size=24)
                .encode(
                    x=alt.X("diataxis_type:N", title=None, sort="-y"),
                    y=alt.Y("days_since_update:Q", title="Median days since update"),
                    tooltip=[alt.Tooltip("diataxis_type:N", title="Type"),
                             alt.Tooltip("days_since_update:Q", title="Median stale days")],
                )
                .properties(height=280)
            )
            st.altair_chart(styled(stale_by_type), use_container_width=True)

        if "todo_flag" in ddf.columns:
            st.subheader("TODO/WIP pages by type")
            todo_counts = (
                ddf.assign(status=np.where(ddf["todo_flag"], "Flagged", "Clean"))
                .groupby(["diataxis_type", "status"], as_index=False)
                .size()
            )
            todo_chart = (
                alt.Chart(todo_counts)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=24)
                .encode(
                    x=alt.X("diataxis_type:N", title=None),
                    y=alt.Y("size:Q", title="Pages", stack="zero"),
                    color=alt.Color(
                        "status:N", title="Status",
                        scale=alt.Scale(domain=["Clean", "Flagged"], range=[GOOD, WARNING]),
                    ),
                    tooltip=[alt.Tooltip("diataxis_type:N", title="Type"),
                             alt.Tooltip("status:N", title="Status"),
                             alt.Tooltip("size:Q", title="Pages")],
                )
                .properties(height=280)
            )
            st.altair_chart(styled(todo_chart), use_container_width=True)

# --------------------------------------------------------------------------- #
# Readability
# --------------------------------------------------------------------------- #
with tab_readability:
    st.subheader("Readability vs. length")
    rdf = fdf.dropna(subset=["flesch_reading_ease"])
    if rdf.empty:
        st.info("No pages with prose to score in the current filter.")
    else:
        base = (
            alt.Chart(rdf)
            .mark_circle(size=80, color=BLUE, opacity=0.75, stroke="#fcfcfb" if MODE == "light" else "#1a1a19",
                         strokeWidth=2)
            .encode(
                x=alt.X("word_count:Q", title="Word count"),
                y=alt.Y("flesch_reading_ease:Q", title="Flesch reading ease"),
                tooltip=[alt.Tooltip("path:N", title="Page"), alt.Tooltip("word_count:Q", title="Words"),
                         alt.Tooltip("flesch_reading_ease:Q", title="Readability", format=".0f")],
            )
            .properties(height=280)
        )
        if "diataxis_type" in rdf.columns and rdf["diataxis_type"].notna().any():
            # Faceted small multiples, not a 4-way categorical scatter: Diátaxis has 4
            # types, past the palette's 3-slot all-pairs cap for scatter/bubble forms.
            chart = base.properties(width=220, height=220).facet(
                column=alt.Column("diataxis_type:N", title=None)
            )
            st.altair_chart(styled(chart), use_container_width=False)
        else:
            st.altair_chart(styled(base), use_container_width=True)

# --------------------------------------------------------------------------- #
# Raw data
# --------------------------------------------------------------------------- #
with tab_raw:
    st.dataframe(fdf.drop(columns=["section"]), hide_index=True, use_container_width=True)
