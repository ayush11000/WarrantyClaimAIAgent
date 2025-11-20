import json
from typing import Dict, List, Literal

import pandas as pd

from state_and_policy import ClaimState
from graph import COMPILED_GRAPH


# -----------------------------
# 5. Public API: process_claims
# -----------------------------


def compute_anomaly_stats(df: pd.DataFrame):
    """
    Pre-compute mean and std for numeric columns we care about.
    Returns (stats, numeric_cols).
    """
    numeric_candidates = [
        "total_cost",
        "labor_cost",
        "part_cost",
        "mileage",
        "previous_claims",
    ]
    numeric_cols = [c for c in numeric_candidates if c in df.columns]

    stats: Dict[str, Dict[str, float]] = {}
    for col in numeric_cols:
        series = pd.to_numeric(df[col], errors="coerce")
        mean = series.mean()
        std = series.std()
        if std == 0 or pd.isna(std):
            std = 1e-6  # avoid division by zero
        stats[col] = {"mean": float(mean), "std": float(std)}
    return stats, numeric_cols


def compute_anomaly_for_row(
    row: pd.Series, stats: Dict[str, Dict[str, float]], numeric_cols: List[str]
):
    """
    Compute per-column z-scores and overall anomaly score for a single row.
    """
    z_scores: Dict[str, float] = {}
    total = 0.0
    count = 0

    for col in numeric_cols:
        value = row.get(col, None)
        if value is None:
            continue

        try:
            v = float(value)
        except Exception:
            continue

        mean = stats[col]["mean"]
        std = stats[col]["std"]
        if std <= 0:
            continue

        z = abs((v - mean) / std)
        z_scores[col] = z
        total += z
        count += 1

    anomaly_score = total / count if count > 0 else 0.0

    if anomaly_score > 2.5:
        bucket: Literal["low", "medium", "high"] = "high"
    elif anomaly_score > 1.5:
        bucket = "medium"
    else:
        bucket = "low"

    return anomaly_score, bucket, z_scores


def process_claims(df: pd.DataFrame, progress_callback=None) -> pd.DataFrame:
    """
    Main entrypoint used by Streamlit app.
    Takes a DataFrame of claims, runs them through the multi-agent graph,
    and returns a DataFrame with additional columns.
    """
    results = []
    total = len(df)

    # Pre-compute anomaly statistics across the batch
    stats, numeric_cols = compute_anomaly_stats(df)

    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        anomaly_score, risk_bucket, z_scores = compute_anomaly_for_row(
            row, stats, numeric_cols
        )

        initial_state: ClaimState = {
            "claim": row.to_dict(),
            "policy_check_summary": None,
            "policy_coverage": None,
            "policy_context": None,
            "fraud_score": None,
            "fraud_reasons": [],
            "evidence_summary": None,
            "decision": None,
            "decision_rationale": None,
            "decision_confidence": None,
            "anomaly_score": anomaly_score,
            "risk_bucket": risk_bucket,
            "anomaly_features": z_scores,
            "hitl_required": False,
            "hitl_notes": None,
            "trace": [],
        }

        final_state = COMPILED_GRAPH.invoke(initial_state)

        result_row = dict(row)

        result_row.update(
            {
                "policy_coverage": final_state.get("policy_coverage"),
                "policy_check_summary": final_state.get("policy_check_summary"),
                "policy_context": final_state.get("policy_context"),
                "fraud_score": final_state.get("fraud_score"),
                "fraud_reasons": "; ".join(final_state.get("fraud_reasons", [])),
                "evidence_summary": final_state.get("evidence_summary"),
                "decision": final_state.get("decision"),
                "decision_rationale": final_state.get("decision_rationale"),
                "decision_confidence": final_state.get("decision_confidence"),
                "hitl_required": final_state.get("hitl_required"),
                "hitl_notes": final_state.get("hitl_notes"),
                "anomaly_score": final_state.get("anomaly_score"),
                "risk_bucket": final_state.get("risk_bucket"),
                "anomaly_features": json.dumps(final_state.get("anomaly_features", {})),
                "trace": "\n".join(final_state.get("trace", [])),
            }
        )

        results.append(result_row)

        if progress_callback is not None:
            progress_callback(idx, total)

    return pd.DataFrame(results)
