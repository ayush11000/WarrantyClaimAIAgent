import json
from typing import List
import os
from langchain_core.prompts import ChatPromptTemplate
from notifications_mcp_client import send_hitl_email

from state_and_policy import ClaimState, get_llm, get_policy_retriever


# -----------------------------
# 3. Agent node implementations
# -----------------------------


def policy_check_agent(state: ClaimState) -> ClaimState:
    """
    Uses vector DB retrieval + LLM to determine policy coverage.
    Returns:
      - policy_coverage ("covered", "not_covered", "unclear")
      - policy_check_summary (clean human-readable text)
      - policy_context (retrieved snippets)
    """
    llm = get_llm()
    retriever = get_policy_retriever()

    claim = state["claim"]
    claim_json = json.dumps(claim, default=str)

    # Build a retrieval query
    parts = []
    for key in ["vehicle_type", "model", "part_replaced", "failure_description"]:
        if key in claim and claim[key] is not None:
            parts.append(f"{key}: {claim[key]}")
    query = " | ".join(parts) or claim_json

    # Retrieve policy snippets
    docs = retriever.invoke(query)
    policy_context = "\n\n---\n\n".join(d.page_content for d in docs)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a senior warranty engineer.\n"
                "You will receive:\n"
                "- Policy text snippets\n"
                "- Claim data as JSON\n\n"
                "Decide whether this claim is covered by the policy.\n"
                "You MUST respond with JSON only (no markdown) with keys:\n"
                "  coverage : one of 'covered', 'not_covered', 'unclear'\n"
                "  summary  : a short natural-language explanation (3–5 sentences)\n"
                "  key_rules: a list of short bullet strings naming the policy rules you used.\n",
            ),
            (
                "user",
                "Policy snippets:\n{policy_context}\n\n"
                "Claim data:\n{claim_json}\n\n"
                "Respond with STRICT JSON that can be parsed by Python json.loads.",
            ),
        ]
    )

    # ✅ Pipe prompt → LLM
    chain = prompt | llm
    msg = chain.invoke(
        {
            "policy_context": policy_context,
            "claim_json": claim_json,
        }
    )

    raw = getattr(msg, "content", msg)
    if isinstance(raw, list):
        raw = " ".join(str(x) for x in raw)
    if not isinstance(raw, str):
        raw = str(raw)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.lstrip()

    coverage = "unclear"
    summary = "Could not parse policy result."
    key_rules: List[str] = []

    try:
        parsed = json.loads(raw)
        coverage = parsed.get("coverage", "unclear")
        summary = parsed.get("summary", summary)
        key_rules = parsed.get("key_rules", []) or []
    except Exception:
        summary = raw

    state["policy_coverage"] = coverage  # type: ignore
    state["policy_check_summary"] = summary
    state["policy_context"] = policy_context

    state["trace"].append(
        f"[policy_check_agent] coverage={coverage}, summary={summary}"
    )
    if key_rules:
        state["trace"].append("[policy_check_agent] key_rules=" + "; ".join(key_rules))
    return state


def fraud_scoring_agent(state: ClaimState) -> ClaimState:
    """
    Combines policy assessment + anomaly stats to produce a fraud score.
    """
    llm = get_llm()

    anomaly_score = state.get("anomaly_score", None)
    risk_bucket = state.get("risk_bucket", None)
    anomaly_features = state.get("anomaly_features", {})

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a warranty fraud analyst.\n"
                "Estimate the likelihood of fraud or abuse based on:\n"
                "- the claim data\n"
                "- policy coverage and summary\n"
                "- statistical anomaly metrics (z-scores).\n\n"
                "Interpret anomaly_score as:\n"
                "  ~0: normal, 1–2: somewhat unusual, >2.5: highly unusual.\n\n"
                "You MUST respond with STRICT JSON with keys:\n"
                "  fraud_score: float in [0, 100]\n"
                "  reasons    : list of short bullet strings explaining the score.\n",
            ),
            (
                "user",
                "Claim data:\n{claim_json}\n\n"
                "Policy coverage: {coverage}\n"
                "Policy summary: {summary}\n\n"
                "Anomaly score (avg z-score): {anomaly_score}\n"
                "Risk bucket: {risk_bucket}\n"
                "Per-field z-scores: {anomaly_features}\n",
            ),
        ]
    )

    chain = prompt | llm
    msg = chain.invoke(
        {
            "claim_json": json.dumps(state["claim"], default=str),
            "coverage": state.get("policy_coverage", "unclear"),
            "summary": state.get("policy_check_summary", ""),
            "anomaly_score": anomaly_score,
            "risk_bucket": risk_bucket,
            "anomaly_features": anomaly_features,
        }
    )

    raw = getattr(msg, "content", msg)
    if isinstance(raw, list):
        raw = " ".join(str(x) for x in raw)
    if not isinstance(raw, str):
        raw = str(raw)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.lstrip()

    fraud_score = 50.0
    reasons: List[str] = []
    try:
        parsed = json.loads(raw)
        fraud_score = float(parsed.get("fraud_score", fraud_score))
        reasons = parsed.get("reasons", []) or []
    except Exception:
        reasons = [f"Unparsed fraud JSON: {raw}"]

    fraud_score = max(0.0, min(100.0, fraud_score))

    state["fraud_score"] = fraud_score
    state["fraud_reasons"] = reasons
    state["trace"].append(
        f"[fraud_scoring_agent] fraud_score={fraud_score}, reasons={'; '.join(reasons)}"
    )
    return state


def evidence_agent(state: ClaimState) -> ClaimState:
    """
    Prepare a concise evidence bundle for auditors / HITL reviewers.
    Uses retrieved policy context + anomaly metrics + fraud score.
    """
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an assistant preparing a concise evidence bundle for a warranty claim.\n"
                "Summarize the most relevant facts, focusing on:\n"
                "- time & mileage vs. policy limits\n"
                "- component category (wear-and-tear vs covered)\n"
                "- suspicious patterns or mitigating factors\n\n"
                "Write 1–2 short paragraphs plus a bullet list of key points.",
            ),
            (
                "user",
                "Claim JSON:\n{claim_json}\n\n"
                "Policy coverage: {policy_coverage}\n"
                "Policy summary:\n{policy_summary}\n\n"
                "Anomaly score: {anomaly_score}\n"
                "Risk bucket: {risk_bucket}\n"
                "Per-field z-scores: {anomaly_features}\n"
                "Fraud score: {fraud_score} / 100\n"
                "Fraud reasons: {fraud_reasons}\n\n"
                "Prepare a concise evidence summary.",
            ),
        ]
    )

    chain = prompt | llm
    msg = chain.invoke(
        {
            "claim_json": json.dumps(state["claim"], default=str),
            "policy_coverage": state.get("policy_coverage", "unclear"),
            "policy_summary": state.get("policy_check_summary", ""),
            "anomaly_score": state.get("anomaly_score", None),
            "risk_bucket": state.get("risk_bucket", None),
            "anomaly_features": state.get("anomaly_features", {}),
            "fraud_score": state.get("fraud_score", None),
            "fraud_reasons": "; ".join(state.get("fraud_reasons", [])),
        }
    )

    evidence_summary = getattr(msg, "content", msg)
    state["evidence_summary"] = evidence_summary
    state["trace"].append("[evidence_agent] evidence_summary generated.")
    return state


def decision_agent(state: ClaimState) -> ClaimState:
    """
    Final decision agent.
    """
    llm = get_llm()

    claim = state.get("claim", {})
    coverage = state.get("policy_coverage", "unclear")
    policy_summary = state.get("policy_check_summary", "")
    fraud_score = state.get("fraud_score", 50)
    fraud_reasons = state.get("fraud_reasons", [])
    anomaly_score = state.get("anomaly_score", 0.0)
    risk_bucket = state.get("risk_bucket", "medium")
    evidence_summary = state.get("evidence_summary", "")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a senior warranty decision specialist.\n"
                "You must decide whether to approve, decline, or escalate this claim for human review.\n\n"
                "You MUST respond with STRICT JSON only, with keys:\n"
                "  decision   : one of 'approve', 'decline', 'escalate_hitl'\n"
                "  rationale  : short explanation (2–4 sentences)\n"
                "  confidence : float in [0, 1] representing your confidence.",
            ),
            (
                "user",
                "Claim JSON:\n{claim_json}\n\n"
                "Policy coverage: {coverage}\n"
                "Policy summary:\n{policy_summary}\n\n"
                "Fraud score: {fraud_score}\n"
                "Fraud reasons: {fraud_reasons}\n\n"
                "Anomaly score: {anomaly_score}\n"
                "Risk bucket: {risk_bucket}\n"
                "Evidence summary:\n{evidence_summary}\n",
            ),
        ]
    )

    chain = prompt | llm
    msg = chain.invoke(
        {
            "claim_json": json.dumps(claim, default=str),
            "coverage": coverage,
            "policy_summary": policy_summary,
            "fraud_score": fraud_score,
            "fraud_reasons": "; ".join(fraud_reasons),
            "anomaly_score": anomaly_score,
            "risk_bucket": risk_bucket,
            "evidence_summary": evidence_summary,
        }
    )

    decision: str = "escalate_hitl"
    rationale = "Decision could not be parsed; defaulting to escalate for human review."
    confidence = 0.0

    raw = getattr(msg, "content", msg)
    if isinstance(raw, list):
        raw = " ".join(str(x) for x in raw)
    if not isinstance(raw, str):
        raw = str(raw)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.lstrip()

    try:
        parsed = json.loads(raw)
        d = str(parsed.get("decision", "")).strip().lower()
        if d in ["approve", "decline", "escalate_hitl"]:
            decision = d  # type: ignore
        rationale = parsed.get("rationale", rationale)
        confidence_raw = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except Exception:
            confidence = 0.0
    except Exception:
        decision = "escalate_hitl"
        rationale = raw
        confidence = 0.0

    state["decision"] = decision
    state["decision_rationale"] = rationale
    state["decision_confidence"] = confidence
    state["trace"].append(
        f"[decision_agent] llm_decision={decision}, confidence={confidence:.2f}, rationale={rationale}"
    )
    return state


def hitl_review_node(state: ClaimState) -> ClaimState:
    """
    Node that marks a claim for human review AND sends an email
    via the notifications 'MCP-like' client.
    """
    state["hitl_required"] = True

    note = (
        "Flagged for human-in-the-loop review based on "
        "policy_coverage={coverage}, fraud_score={score}, risk_bucket={risk}."
    ).format(
        coverage=state.get("policy_coverage", "unclear"),
        score=state.get("fraud_score", 50),
        risk=state.get("risk_bucket", "unknown"),
    )

    claim = state.get("claim", {}) or {}
    claim_id = str(claim.get("claim_id") or claim.get("id") or "UNKNOWN-CLAIM")
    decision = state.get("decision", "escalate_hitl") or "escalate_hitl"
    fraud_score = float(state.get("fraud_score") or 0.0)
    risk_bucket = str(state.get("risk_bucket") or "unknown")
    evidence_summary = state.get("evidence_summary") or ""

    state["hitl_notes"] = note

    # Try to send the email; don't crash the graph if it fails
    try:
        send_hitl_email(
            claim_id=claim_id,
            to_email=None,  # use EMAIL_HITL_TO by default
            decision=decision,
            fraud_score=fraud_score,
            risk_bucket=risk_bucket,
            notes=note,
            evidence_summary=evidence_summary,
        )
        state["hitl_email_sent"] = True
        state["hitl_email_error"] = None
        state["hitl_email_recipient"] = os.getenv("EMAIL_HITL_TO")
        state["trace"].append(
            f"[hitl_review_node] Marked for HITL review and email sent for claim {claim_id}."
        )
    except Exception as e:
        # Log the error but keep going
        state["hitl_email_sent"] = False
        state["hitl_email_error"] = str(e)
        state["hitl_email_recipient"] = os.getenv("EMAIL_HITL_TO")
        state["trace"].append(
            f"[hitl_review_node] Marked for HITL review BUT email failed: {e}"
        )

    return state

