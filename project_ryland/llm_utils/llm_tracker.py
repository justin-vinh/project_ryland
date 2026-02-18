"""
------------------------------------------------------------------------------
Author:         Justin Vinh
Institution:    Dana-Farber Cancer Institute
Working Groups: Lindvall & Rhee Labs
Parent Package: Project Ryland
Creation Date:  2026.02.10
Last Modified:  2026.02.18

Purpose:
Parse Project Ryland llm_tracking.log files and maintain a structured
CSV summary of completed LLM runs.
------------------------------------------------------------------------------
Designed for notebook use via import — not command line usage.

Extracted fields per completed run:
    - DATE
    - RUN_ID
    - MODEL
    - OUTPUT_FILE
    - COST
    - ROWS_TOTAL
    - DURATION_MIN

Example
-------
from track_costs import update_run_summary

df = update_run_summary(
    log_path="output_llm/llm_tracking.log",
    csv_path="output_llm/run_summary.csv"
)
"""

import re
from pathlib import Path
from typing import List, Dict

import pandas as pd


# ---------------------------------------------------------------------
# Log Parsing
# ---------------------------------------------------------------------

def _parse_completed_runs(log_text: str) -> List[Dict]:
    """
    Parse completed LLM runs from a tracking log string.
    """

    runs = []

    blocks = re.split(r"-{10,}", log_text)

    for block in blocks:

        if "Final LLM output saved:" not in block:
            continue

        # -------------------------
        # OUTPUT FILE + PATH
        # -------------------------
        m_out = re.search(r"Final LLM output saved:\s+(.+)", block)
        if not m_out:
            continue

        output_path = m_out.group(1).strip()
        output_file = Path(output_path).name

        # -------------------------
        # INPUT FILE + PATH
        # -------------------------
        m_in = re.search(r"Loading data from:\s+(.+)", block)
        input_path = m_in.group(1).strip() if m_in else ""
        input_file = Path(input_path).name if input_path else ""

        # -------------------------
        # MODEL + RUN_ID
        # -------------------------
        m_file = re.search(
            r"final_(?P<model>.+?)_(?P<runid>\d{8}_\d{4})\.csv",
            output_file
        )
        if not m_file:
            continue

        model = m_file.group("model")
        run_id = m_file.group("runid")

        date = run_id[:8]
        date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

        # -------------------------
        # COST
        # -------------------------
        m_cost = re.search(r"Total': '\$(\d+\.\d+)'", block)
        cost_usd = float(m_cost.group(1)) if m_cost else None

        # -------------------------
        # ROWS TOTAL
        # -------------------------
        m_rows = re.findall(r"CHECKPOINT: Total:\s*(\d+)", block)
        rows_total = int(m_rows[-1]) if m_rows else None

        # -------------------------
        # DURATION
        # -------------------------
        m_dur = re.search(r"Duration:\s*([\d.]+)\s*min", block)
        duration_min = float(m_dur.group(1)) if m_dur else None

        runs.append({
            "DATE": date_fmt,
            "RUN_ID": run_id,
            "MODEL": model,
            "COST_USD": cost_usd,
            "ROWS_TOTAL": rows_total,
            "DURATION_MIN": duration_min,
            "INPUT_FILE": input_file,
            "OUTPUT_FILE": output_file,
            "OUTPUT_PATH": output_path,
            "INPUT_PATH": input_path
        })

    return runs


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def update_run_summary(
    log_path: str | Path,
    csv_path: str | Path
) -> pd.DataFrame:
    """
    Parse a tracking log and update a CSV run summary table.

    Safe for repeated use — prevents duplicate RUN_ID entries.

    Parameters
    ----------
    log_path : str or Path
        Path to llm_tracking.log file

    csv_path : str or Path
        Path to summary CSV file (created if missing)

    Returns
    -------
    pandas.DataFrame
        Updated run summary table
    """

    log_path = Path(log_path)
    csv_path = Path(csv_path)

    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    log_text = log_path.read_text()

    runs = _parse_completed_runs(log_text)

    if not runs:
        print("No completed runs found.")
        return pd.DataFrame()

    new_df = pd.DataFrame(runs)

    # -------------------------
    # Merge with existing CSV
    # -------------------------
    if csv_path.exists():
        existing_df = pd.read_csv(csv_path)
        combined = pd.concat([existing_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset="RUN_ID", keep="last")
    else:
        combined = new_df

    combined = combined.sort_values("RUN_ID")

    # Ensure OUTPUT_PATH is last column
    cols = list(combined.columns)
    if "OUTPUT_PATH" in cols:
        cols = [c for c in cols if c != "OUTPUT_PATH"] + ["OUTPUT_PATH"]
        combined = combined[cols]

    combined.to_csv(csv_path, index=False)

    print(f"Updated run summary file:   {csv_path}")
    print(f"Total recorded LLM runs:    {len(combined)}")

    return combined
