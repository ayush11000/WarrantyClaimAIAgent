import streamlit as st
import pandas as pd
from main import process_claims
from processing import process_claims

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Warranty Fraud Analysis Console", layout="wide")

st.title("Warranty Fraud Analysis Console")
st.caption(
    "Upload warranty claims, run the multi-agent workflow (policy, fraud, anomaly, decision), "
    "and optionally apply human overrides."
)

# -----------------------------
# Sidebar: upload & run
# -----------------------------
with st.sidebar:
    st.header("1. Upload & Run")

    uploaded_file = st.file_uploader("Claims CSV", type=["csv"])

    st.markdown(
        "Expected: one claim per row (e.g., `claim_id`, dates, mileage, part_replaced, costs, etc.)."
    )

    run_button = st.button("Run analysis", use_container_width=True)

    st.markdown("---")
    st.header("2. Export")

    if "results_df" in st.session_state and st.session_state["results_df"] is not None:
        _df = st.session_state["results_df"]
        csv_bytes = _df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download full results (CSV)",
            data=csv_bytes,
            file_name="processed_claims_with_overrides.csv",
            mime="text/csv",
            use_container_width=True,
        )

        overrides_df = _df[_df["human_decision"].notnull()] if "human_decision" in _df.columns else pd.DataFrame()
        if not overrides_df.empty:
            log_cols = [
                c
                for c in [
                    "claim_id",
                    "decision",
                    "final_decision",
                    "human_decision",
                    "human_comment",
                    "fraud_score",
                    "policy_coverage",
                    "hitl_notes",
                ]
                if c in overrides_df.columns
            ]
            overrides_csv = overrides_df[log_cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download override log (CSV)",
                data=overrides_csv,
                file_name="override_log.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.caption("No human overrides yet.")

    else:
        st.caption("Run the analysis to enable downloads.")


# -----------------------------
# Process input when button clicked
# -----------------------------
results_df = st.session_state.get("results_df", None)

if run_button:
    if uploaded_file is None:
        st.error("Please upload a CSV file before running the analysis.")
    else:
        try:
            input_df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            input_df = None

        if input_df is not None:
            with st.spinner("Running multi-agent warranty + fraud analysis..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_cb(current, total):
                    pct = int(current / total * 100)
                    progress_bar.progress(pct)
                    status_text.info(f"Processing {current}/{total} claims...")

                results_df = process_claims(input_df, progress_callback=progress_cb)

            # Initialize override-related columns if missing
            if results_df is not None:
                if "final_decision" not in results_df.columns:
                    results_df["final_decision"] = results_df["decision"]
                if "human_decision" not in results_df.columns:
                    results_df["human_decision"] = None
                if "human_comment" not in results_df.columns:
                    results_df["human_comment"] = None

            st.session_state["results_df"] = results_df
            progress_bar.progress(100)
            status_text.success("Analysis complete.")

# -----------------------------
# If no results yet, show instructions
# -----------------------------
if results_df is None:
    st.info(
        "Upload a claims CSV in the sidebar and click **Run analysis** to see results. "
        "You’ll then get an overview, HITL review tab, full table, and agent traces."
    )
    st.stop()

# Ensure override columns exist in case of old sessions
for col in ["final_decision", "human_decision", "human_comment"]:
    if col not in results_df.columns:
        if col == "final_decision":
            results_df[col] = results_df.get("decision")
        else:
            results_df[col] = None

# -----------------------------
# Main tabs
# -----------------------------
tab_overview, tab_hitl, tab_all, tab_traces = st.tabs(
    ["Overview", "HITL Review", "All Results", "Agent Traces"]
)

# -----------------------------
# Overview tab
# -----------------------------
with tab_overview:
    st.subheader("Summary metrics")

    total = len(results_df)
    approves = int((results_df["final_decision"] == "approve").sum())
    declines = int((results_df["final_decision"] == "decline").sum())
    escalates = int((results_df["final_decision"] == "escalate_hitl").sum())

    avg_fraud = float(results_df["fraud_score"].mean()) if "fraud_score" in results_df.columns else None
    avg_anomaly = float(results_df["anomaly_score"].mean()) if "anomaly_score" in results_df.columns else None

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Total claims", total)
    col_b.metric("Approved (final)", approves)
    col_c.metric("Declined (final)", declines)
    col_d.metric("Escalated (final)", escalates)

    st.markdown("")

    # Risk bucket distribution row
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    if "risk_bucket" in results_df.columns:
        risk_counts = results_df["risk_bucket"].value_counts().to_dict()
        low_count = int(risk_counts.get("low", 0))
        med_count = int(risk_counts.get("medium", 0))
        high_count = int(risk_counts.get("high", 0))
        col_r1.metric("Low risk claims", low_count)
        col_r2.metric("Medium risk claims", med_count)
        col_r3.metric("High risk claims", high_count)
    else:
        col_r1.caption("No risk_bucket column found.")

    if avg_fraud is not None:
        col_r3.metric("Average fraud score", f"{avg_fraud:.1f}")
    if avg_anomaly is not None:
        col_r4.metric("Average anomaly score", f"{avg_anomaly:.2f}")

    st.markdown("---")
    st.subheader("Quick table")

    quick_cols = [
        c
        for c in [
            "claim_id",
            "model",
            "part_replaced",
            "total_cost",
            "fraud_score",
            "anomaly_score",
            "risk_bucket",
            "policy_coverage",
            "final_decision",
        ]
        if c in results_df.columns
    ]
    if quick_cols:
        st.dataframe(results_df[quick_cols].head(15), use_container_width=True)
    else:
        st.caption("No standard columns found for quick view; showing first 10 rows instead.")
        st.dataframe(results_df.head(10), use_container_width=True)

    st.markdown("---")
    st.subheader("Selected claim summary")

    sel_idx = st.selectbox(
        "Pick a claim to inspect",
        options=list(results_df.index),
        format_func=lambda i: f"Row {i} – claim_id={results_df.loc[i].get('claim_id', 'N/A')}",
    )

    row = results_df.loc[sel_idx]

    # Top-line cards for this claim
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final decision", row.get("final_decision", "N/A"))
    c2.metric("Fraud score", f"{row.get('fraud_score', 'N/A')}")
    c3.metric("Anomaly score", f"{row.get('anomaly_score', 'N/A')}")
    c4.metric("Risk bucket", row.get("risk_bucket", "N/A"))

    st.markdown("")

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.markdown("#### Raw claim fields")
        # Show a compact table of original claim columns (exclude AI columns)
        exclude_cols = {
            "policy_coverage",
            "policy_check_summary",
            "policy_context",
            "fraud_score",
            "fraud_reasons",
            "evidence_summary",
            "decision",
            "decision_rationale",
            "hitl_required",
            "hitl_notes",
            "anomaly_score",
            "risk_bucket",
            "anomaly_features",
            "final_decision",
            "human_decision",
            "human_comment",
            "trace",
        }
        raw_data = {k: v for k, v in row.items() if k not in exclude_cols}
        st.table(pd.DataFrame(raw_data, index=["value"]).T)

    with col_right:
        st.markdown("#### Policy assessment")
        st.write(f"**Coverage:** {row.get('policy_coverage', 'N/A')}")
        st.write(f"**Summary:** {row.get('policy_check_summary', '')}")
        if "policy_context" in results_df.columns and isinstance(row.get("policy_context"), str):
            with st.expander("Relevant policy snippets", expanded=False):
                st.write(row.get("policy_context"))

    st.markdown("---")

    c_l, c_r = st.columns(2)

    with c_l:
        st.markdown("#### Fraud & anomaly view")
        st.write(f"**Fraud score:** {row.get('fraud_score', 'N/A')}")
        st.write(f"**Fraud reasons:** {row.get('fraud_reasons', '')}")
        st.write(f"**Anomaly score:** {row.get('anomaly_score', 'N/A')}")
        st.write(f"**Risk bucket:** {row.get('risk_bucket', 'N/A')}")
        if isinstance(row.get("anomaly_features"), str):
            with st.expander("Per-feature z-scores", expanded=False):
                st.json(row.get("anomaly_features"))

    with c_r:
        st.markdown("#### Decision rationale")
        st.write(f"**AI decision:** {row.get('decision', 'N/A')}")
        st.write(f"**Final decision (after override):** {row.get('final_decision', 'N/A')}")
        st.write(f"**AI rationale:** {row.get('decision_rationale', '')}")
        if row.get("human_decision") not in [None, "", float("nan")]:
            st.write(f"**Human override:** {row.get('human_decision')}")
            st.write(f"**Reviewer comment:** {row.get('human_comment', '')}")

# -----------------------------
# HITL Review tab
# -----------------------------
with tab_hitl:
    st.subheader("Human-in-the-loop review")

    if "hitl_required" not in results_df.columns:
        st.info("No HITL flag column found in results.")
    else:
        hitl_df = results_df[results_df["hitl_required"] == True]  # noqa: E712

        if hitl_df.empty:
            st.info("No claims have been flagged for human review.")
        else:
            cols_to_show = [
                c
                for c in [
                    "claim_id",
                    "model",
                    "part_replaced",
                    "fraud_score",
                    "anomaly_score",
                    "risk_bucket",
                    "policy_coverage",
                    "decision",
                    "final_decision",
                    "hitl_notes",
                    "human_decision",
                ]
                if c in hitl_df.columns
            ]
            st.markdown("**Flagged claims**")
            st.dataframe(hitl_df[cols_to_show], use_container_width=True)

            st.markdown("---")
            st.markdown("#### Review & override")

            selected_index = st.selectbox(
                "Select a flagged claim",
                options=list(hitl_df.index),
                format_func=lambda idx: f"Row {idx} – claim_id={results_df.loc[idx].get('claim_id', 'N/A')}",
            )

            selected_row = results_df.loc[selected_index]

            # Claim & AI info
            with st.expander("Claim details", expanded=True):
                exclude_cols = {"trace"}
                st.json({k: v for k, v in selected_row.items() if k not in exclude_cols})

            with st.expander("AI assessment", expanded=False):
                st.write(f"**Policy coverage:** {selected_row.get('policy_coverage')}")
                st.write(f"**Fraud score:** {selected_row.get('fraud_score')}")
                st.write(f"**Anomaly score:** {selected_row.get('anomaly_score')}")
                st.write(f"**Risk bucket:** {selected_row.get('risk_bucket')}")
                st.write(f"**AI decision:** {selected_row.get('decision')}")
                st.write(f"**AI rationale:** {selected_row.get('decision_rationale')}")
                st.write("**Evidence summary:**")
                st.write(selected_row.get("evidence_summary", ""))

            st.markdown("##### Human override")

            human_dec = selected_row.get("human_decision")
            if pd.isna(human_dec):
                human_dec = None

            options = ["keep_ai", "approve", "decline", "escalate_hitl"]
            if human_dec is None:
                default_idx = 0
            else:
                default_idx = options.index(human_dec) if human_dec in options else 0

            override_choice = st.radio(
                "Final decision (after review)",
                options=options,
                index=default_idx,
                format_func=lambda x: {
                    "keep_ai": "Keep AI decision",
                    "approve": "Override to APPROVE",
                    "decline": "Override to DECLINE",
                    "escalate_hitl": "Keep as ESCALATE_HITL",
                }[x],
            )

            human_comment = st.text_area(
                "Reviewer comment (required if overriding AI decision)",
                value=(selected_row.get("human_comment") or ""),
                height=120,
            )

            if st.button("Apply override", type="primary"):
                df = st.session_state["results_df"]

                if override_choice == "keep_ai":
                    df.at[selected_index, "human_decision"] = None
                    df.at[selected_index, "human_comment"] = None
                    df.at[selected_index, "final_decision"] = df.at[selected_index, "decision"]
                    st.success("Override cleared. Final decision now matches AI decision.")
                else:
                    if not human_comment.strip():
                        st.error("Please provide a reviewer comment when overriding the AI decision.")
                    else:
                        df.at[selected_index, "human_decision"] = override_choice
                        df.at[selected_index, "human_comment"] = human_comment.strip()
                        df.at[selected_index, "final_decision"] = override_choice
                        st.success("Override applied. Final decision updated.")

                st.session_state["results_df"] = df
                results_df = df

# -----------------------------
# All Results tab
# -----------------------------
with tab_all:
    st.subheader("All results (including overrides)")

    def style_decision(val):
        if val == "approve":
            return "background-color: #d1fae5; color: #065f46"
        if val == "decline":
            return "background-color: #fee2e2; color: #7f1d1d"
        if val == "escalate_hitl":
            return "background-color: #fff7ed; color: #92400e"
        return ""

    if "final_decision" in results_df.columns:
        styled = results_df.style.applymap(style_decision, subset=["final_decision"])
        st.dataframe(styled, use_container_width=True)
    else:
        st.dataframe(results_df, use_container_width=True)

# -----------------------------
# Agent Traces tab
# -----------------------------
with tab_traces:
    st.subheader("Agent conversation trace")

    if "trace" not in results_df.columns:
        st.info("No trace column present in results.")
    else:
        sel_idx = st.selectbox(
            "Select a claim",
            options=list(results_df.index),
            format_func=lambda i: f"Row {i} – claim_id={results_df.loc[i].get('claim_id', 'N/A')}",
        )

        row = results_df.loc[sel_idx]
        trace = row.get("trace", "")

        if not isinstance(trace, str) or not trace.strip():
            st.info("No agent trace available for this claim.")
        else:
            steps = [s for s in trace.split("\n") if s.strip()]
            for step in steps:
                title = step.split("]")[0] + "]" if step.startswith("[") else "Step"
                with st.expander(title, expanded=False):
                    st.markdown(step)
