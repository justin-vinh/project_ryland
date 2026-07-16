"""
------------------------------------------------------------------------------
Author:         Justin Vinh
Institution:    Dana-Farber Cancer Institute
Working Groups: Lindvall & Rhee Labs
Parent Package: Project Ryland
Creation Date:  2026.02.10
Last Modified:  2026.02.23

Purpose:
Parse Project Ryland llm_tracking.log files and maintain a structured
CSV summary of LLM runs (including interrupted runs).
------------------------------------------------------------------------------
"""

import re
from pathlib import Path
from typing import List, Dict
import pandas as pd


# =============================================================================
# LEGACY PARSER
# =============================================================================

def _parse_completed_runs(log_text: str) -> List[Dict]:
    """
    Legacy parser (completed runs only).
    """

    runs = []
    blocks = re.split(r"-{10,}", log_text)

    for block in blocks:

        if "Final LLM output saved:" not in block:
            continue

        m_out = re.search(r"Final LLM output saved:\s+(.+)", block)
        if not m_out:
            continue

        output_path = m_out.group(1).strip()
        output_file = Path(output_path).name

        m_in = re.search(r"Loading data from:\s+(.+)", block)
        input_path = m_in.group(1).strip() if m_in else ""
        input_file = Path(input_path).name if input_path else ""

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

        m_cost = re.search(r"Total': '\$(\d+\.\d+)'", block)
        cost_usd = float(m_cost.group(1)) if m_cost else None

        m_rows = re.findall(r"CHECKPOINT: Total:\s*(\d+)", block)
        rows_total = int(m_rows[-1]) if m_rows else None

        m_dur = re.search(r"Duration:\s*([\d.]+)\s*min", block)
        duration_min = float(m_dur.group(1)) if m_dur else None

        # RUN TAG (may be absent in legacy logs)
        m_tag = re.search(r"Run tag:\s+(.+)", block)
        run_tag = m_tag.group(1).strip() if m_tag else None

        runs.append({
            "RUN_ID": run_id,
            "RUN_TAG": run_tag,
            "STATUS": "SUCCESS",
            "DATE": date_fmt,
            "MODEL": model,
            "COST_USD": cost_usd,
            "ROWS_TOTAL": rows_total,
            "DURATION_MIN": duration_min,
            "INPUT_FILE": input_file,
            "OUTPUT_FILE": output_file,
            "OUTPUT_PATH": output_path,
            "INPUT_PATH": input_path,
            "RESUMED_FROM_CHECKPOINT": False
        })

    return runs


# =============================================================================
# NEW PARSER (AUDIT VERSION)
# =============================================================================

def _parse_completed_runs_v2(log_text: str) -> List[Dict]:
    """
    Parse new log format with explicit Unique Run ID.

    - '=====' marks start of run
    - Uses logged Unique Run ID (with seconds precision)
    - Logs SUCCESS and INTERRUPTED
    - Cost = latest cumulative or final cost
    - Detects resumed runs
    - Scrapes prompt struct and prompt name
    - Scrapes run tag
    """

    runs = []
    blocks = re.split(r"=+", log_text)

    for block in blocks:

        if "[START] New LLM generation run starting" not in block:
            continue

        # -------------------------
        # RUN ID (required)
        # -------------------------
        m_run = re.search(r"Unique Run ID:\s*(\d{8}_\d{6})", block)
        if not m_run:
            continue

        run_id = m_run.group(1)
        date = run_id[:8]
        date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

        # -------------------------
        # RUN TAG (optional; may be logged as "None")
        # -------------------------
        m_tag = re.search(r"Run tag:\s+(.+)", block)
        run_tag = m_tag.group(1).strip() if m_tag else None
        if run_tag in ("None", ""):
            run_tag = None

        # -------------------------
        # STATUS
        # -------------------------
        completed = "Final LLM output saved:" in block
        status = "SUCCESS" if completed else "INTERRUPTED"

        # -------------------------
        # MODEL
        # -------------------------
        m_model = re.search(r"Loading LLM model:\s+(.+)", block)
        model = m_model.group(1).strip() if m_model else None

        # -------------------------
        # PROMPT STRUCT + PROMPT NAME
        # -------------------------
        m_prompt_struct = re.search(r"Loading prompt struct:\s+(.+)", block)
        prompt_struct = m_prompt_struct.group(1).strip() if m_prompt_struct else None

        m_prompt_name = re.search(r"Loading prompt:\s+(.+)", block)
        prompt_name = m_prompt_name.group(1).strip() if m_prompt_name else None

        # -------------------------
        # INPUT FILE
        # -------------------------
        m_in = re.search(r"Loading input data:\s+(.+)", block)
        input_path = m_in.group(1).strip() if m_in else ""
        input_file = Path(input_path).name if input_path else ""

        # -------------------------
        # OUTPUT FILE (if completed)
        # -------------------------
        m_out = re.search(r"Final LLM output saved:\s+(.+)", block)
        output_path = m_out.group(1).strip() if m_out else ""
        output_file = Path(output_path).name if output_path else ""

        # -------------------------
        # COST (latest cumulative OR final, with unit detection)
        # -------------------------
        cost_matches = re.findall(
            r'"Total":\s*([A-Za-z$]+)\s*(\d+\.\d+)',
            block
        )

        cost_dict = {}

        if cost_matches:
            unit, value = cost_matches[-1]

            # Normalize unit name
            if unit == "$":
                unit_key = "USD"
            else:
                unit_key = unit.upper()

            cost_dict[f"COST_{unit_key}"] = float(value)

        # Backward compatibility
        cost_usd = cost_dict.get("COST_USD", None)

        # -------------------------
        # ROWS + RESUME DETECTION
        # -------------------------
        checkpoint_matches = re.findall(
            r"CHECKPOINT:\s*Total:\s*(\d+),\s*Processed:\s*(\d+)",
            block
        )

        rows_total = None
        resumed = False

        if checkpoint_matches:
            rows_total = int(checkpoint_matches[-1][0])
            for total, processed in checkpoint_matches:
                if int(processed) > 0:
                    resumed = True
                    break

        # -------------------------
        # DURATION (latest)
        # -------------------------
        dur_matches = re.findall(
            r"(?:Duration|Time elapsed):\s*([\d.]+)\s*min",
            block
        )
        duration_min = float(dur_matches[-1]) if dur_matches else None

        runs.append({
            "RUN_ID": run_id,
            "RUN_TAG": run_tag,
            "STATUS": status,
            "DATE": date_fmt,
            "MODEL": model,
            "COST_USD": cost_usd,  # keep for backward compatibility
            **cost_dict,
            "ROWS_TOTAL": rows_total,
            "DURATION_MIN": duration_min,
            "PROMPT_NAME": prompt_name,
            "PROMPT_STRUCT": prompt_struct,
            "INPUT_FILE": input_file,
            "OUTPUT_FILE": output_file,
            "OUTPUT_PATH": output_path,
            "INPUT_PATH": input_path,
            "RESUMED_FROM_CHECKPOINT": resumed
        })

    return runs


# =============================================================================
# PUBLIC API
# =============================================================================

def update_run_summary(
    log_path: str | Path,
    csv_path: str | Path,
    legacy: bool = False
) -> pd.DataFrame:

    log_path = Path(log_path)
    csv_path = Path(csv_path)

    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    log_text = log_path.read_text()

    runs = (
        _parse_completed_runs(log_text)
        if legacy
        else _parse_completed_runs_v2(log_text)
    )

    if not runs:
        print("No runs found.")
        return pd.DataFrame()

    new_df = pd.DataFrame(runs)

    if csv_path.exists():
        existing_df = pd.read_csv(csv_path)
        combined = pd.concat([existing_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset="RUN_ID", keep="last")
    else:
        combined = new_df

    combined = combined.sort_values("RUN_ID")

    # -------------------------
    # Force exact column order
    # -------------------------
    cols_order = [
        "RUN_ID",
        "RUN_TAG",
        "STATUS",
        "DATE",
        "MODEL",
        "COST_USD",
        "ROWS_TOTAL",
        "DURATION_MIN",
        "PROMPT_NAME",
        "PROMPT_STRUCT",
        "INPUT_FILE",
        "OUTPUT_FILE",
        "OUTPUT_PATH",
        "INPUT_PATH",
        "RESUMED_FROM_CHECKPOINT"
    ]

    # Ensure all required columns exist
    for col in cols_order:
        if col not in combined.columns:
            combined[col] = None

    # Keep known columns first, then dynamically add cost columns
    cost_cols = [col for col in combined.columns if col.startswith("COST_")]

    final_cols = cols_order + [c for c in cost_cols if c not in cols_order]

    combined = combined[final_cols]

    combined.to_csv(csv_path, index=False)

    print(f"Updated run summary file: {csv_path}")
    print(f"Total recorded runs:      {len(combined)}")

    return combined