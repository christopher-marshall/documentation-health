"""Command-line interface for dochealth.

    dochealth extract <repo> --config <config.py> [--out metrics.csv] [--diataxis-csv labels.csv]
    dochealth dashboard [metrics.csv]

Both point at a repo/CSV wherever it actually lives on disk - dochealth doesn't
need to be checked out alongside the repo being analyzed.
"""
import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import pandas as pd

from .core import extract_docs


def _load_config(config_path: Path) -> dict:
    spec = importlib.util.spec_from_file_location("_dochealth_user_config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CONFIG


def _cmd_extract(args: argparse.Namespace) -> None:
    config = _load_config(Path(args.config))
    df = extract_docs(Path(args.repo), config)
    if args.diataxis_csv:
        df = df.merge(pd.read_csv(args.diataxis_csv), on="path", how="left")

    if args.out:
        df.to_csv(args.out, index=False)
        print(f"Wrote {len(df)} rows to {args.out}", file=sys.stderr)
    else:
        print(df.to_csv(index=False))


def _cmd_dashboard(args: argparse.Namespace) -> None:
    app_path = Path(__file__).parent / "app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    if args.csv:
        cmd += ["--", args.csv]
    subprocess.run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(prog="dochealth")
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser(
        "extract", help="Run extract_docs() against a cloned repo and save/print the metrics table.")
    p_extract.add_argument("repo", help="Path to a locally cloned docs-as-code repo.")
    p_extract.add_argument("--config", required=True, help="Path to a Python file defining a CONFIG dict.")
    p_extract.add_argument("--diataxis-csv", help="Optional CSV of path,diataxis_type to merge in.")
    p_extract.add_argument("--out", help="Write the metrics table here as CSV (default: print to stdout).")
    p_extract.set_defaults(func=_cmd_extract)

    p_dashboard = sub.add_parser("dashboard", help="Launch the Streamlit dashboard.")
    p_dashboard.add_argument("csv", nargs="?", help="Metrics CSV to preload (default: pick a source in the sidebar).")
    p_dashboard.set_defaults(func=_cmd_dashboard)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
