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

# Diataxis type is subjective and requires manual review. polars_diataxis_types.csv
# covers all pages under user-guide/: the 14 under expressions/ were read and
# labeled by hand, the rest were seeded by suggest_diataxis.py and haven't been
# reviewed - don't treat those as ground truth without checking them yourself.
diataxis = pd.read_csv(Path(__file__).parent / "polars_diataxis_types.csv")
df = df.merge(diataxis, on="path", how="left")

print(df.describe(include="all"))
