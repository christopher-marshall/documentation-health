"""Worked example: run doc_health against a local clone of Polars.

    git clone https://github.com/pola-rs/polars
    python examples/run_polars_example.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from doc_health import extract_docs
from polars_config import CONFIG

df = extract_docs(Path("polars"), CONFIG)

# Diataxis type (tutorial / how-to / reference / explanation) is a judgment call,
# not something the library computes - see the brief's own framing of it as
# "your expertise showing." polars_diataxis_types.csv only labels the 14 pages
# under expressions/ as a worked sample; label the rest by hand before relying
# on this column for a full run.
diataxis = pd.read_csv(Path(__file__).parent / "polars_diataxis_types.csv")
df = df.merge(diataxis, on="path", how="left")

print(df.describe(include="all"))
