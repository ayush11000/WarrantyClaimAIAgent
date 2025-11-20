# Warranty Claim AI Agent

A demo / research project that runs a multi-agent warranty-claim pipeline. It combines:

- a simple anomaly detector for numeric claim fields,
- retrieval + LLM-based policy checks,
- LLM-based fraud scoring and evidence synthesis,
- a final LLM decision agent that can escalate claims for human review (HITL), and
- a Streamlit app (`app.py`) for interactive review and overrides.

This repository is a tutorial/demo and not production-ready. Treat API keys, PII, and real customer data with appropriate security and compliance controls before using in production.

## Features

- Batch processing of claims using `processing.process_claims()`
- Policy retrieval and LLM-driven policy check (`agents.policy_check_agent`)
- Fraud scoring (`agents.fraud_scoring_agent`) and evidence bundling (`agents.evidence_agent`)
- Final decision agent with human-in-the-loop escalation (`agents.decision_agent`, `agents.hitl_review_node`)
- Streamlit UI for running analysis, reviewing flagged claims, applying overrides, and downloading results

## Quick start (macOS / zsh)

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Create a local `.env` file (see `Environment variables` below) or export required variables in your shell.

4. Run the Streamlit UI:

```bash
streamlit run app.py
```

Alternatively, run the demo runner that processes a few claims:

```bash
python main.py
```

## Environment variables

Based on the `.env` you shared, the project expects the following environment variables (store these in a local `.env`, and do NOT commit your real `.env` to the repository):

- `OPENAI_API_KEY` — your OpenAI or Azure OpenAI API key (used by `state_and_policy.get_llm()`)
- `OPENAI_MODEL` — model/deployment name (e.g. `gpt-4o`, `gpt-4o-mini`, or your Azure deployment alias)
- `EMAIL_SMTP_HOST` — SMTP server host for sending HITL notification emails (e.g. `smtp.gmail.com`)
- `EMAIL_SMTP_PORT` — SMTP port (e.g. `587`)
- `EMAIL_SMTP_USER` — SMTP username
- `EMAIL_SMTP_PASSWORD` — SMTP password or app-specific password (keep secret)
- `EMAIL_FROM` — From address used when sending notifications
- `EMAIL_HITL_TO` — Recipient address for HITL notification emails

Example `.env` (DO NOT commit):

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=you@example.com
EMAIL_SMTP_PASSWORD=supersecret
EMAIL_FROM=you@example.com
EMAIL_HITL_TO=reviewer@example.com
```

Notes:
- If your `state_and_policy.py` or other code expects Azure-specific names such as `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_ENDPOINT`, you can set both the `OPENAI_*` and `AZURE_OPENAI_*` variants, or update `state_and_policy.py` to read your chosen names.
- Keep secrets out of Git. Consider adding `.env` to `.gitignore` (already added earlier).

## Project layout

- `app.py` — Streamlit web UI
- `main.py` — tiny runner that processes example claims from `data/`
- `processing.py` — batch processing, anomaly scoring, and the `process_claims()` API used by the app
- `agents.py` — policy/fraud/evidence/decision agent implementations
- `state_and_policy.py` — helper utilities to configure LLMs, retrieval, and the `ClaimState` type
- `graph.py` — LangGraph graph definition used to wire the agents together
- `notifications_mcp_client.py` — helper to send HITL emails
- `data/` — example CSVs and policy PDF used by the demo
- `requirements.txt` — Python dependencies

## Example usage (programmatic)

```python
import pandas as pd
from processing import process_claims

df = pd.read_csv("data/warranty_claims.csv")
results = process_claims(df)
print(results.head())
```

The Streamlit app uses the same `process_claims()` function and exposes a UI for reviewing and overriding decisions.

## Data & privacy

- The repository contains small demo data under `data/` for illustration. Do not commit production data or secrets.
- If your CSVs are large or contain PII, keep them out of version control (add to `.gitignore`).

## Development notes & next steps

- I can add a `.env.example` template (I recommend this).
- Add automated tests for critical graph nodes and a CI workflow (GitHub Actions) to run linting and tests.
- Consider adding a small Dockerfile for reproducible runtimes.

## License

MIT

---

If you'd like me to add a `.env.example`, or a minimal GitHub Actions workflow, say which and I'll add it.
````markdown
# Warranty Claim AI Agent

A demo / research project that runs a multi-agent warranty-claim pipeline. It combines:

- a simple anomaly detector for numeric claim fields,
- retrieval + LLM-based policy checks,
- LLM-based fraud scoring and evidence synthesis,
- a final LLM decision agent that can escalate claims for human review (HITL), and
- a Streamlit app (`app.py`) for interactive review and overrides.

This repository is a tutorial/demo and not production-ready. Treat API keys, PII, and real customer data with appropriate security and compliance controls before using in production.

## Features

- Batch processing of claims using `processing.process_claims()`
- Policy retrieval and LLM-driven policy check (`agents.policy_check_agent`)
- Fraud scoring (`agents.fraud_scoring_agent`) and evidence bundling (`agents.evidence_agent`)
- Final decision agent with human-in-the-loop escalation (`agents.decision_agent`, `agents.hitl_review_node`)
- Streamlit UI for running analysis, reviewing flagged claims, applying overrides, and downloading results

## Quick start (macOS / zsh)

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Create a `.env` file (see `Environment variables` below) or export required variables in your shell.

4. Run the Streamlit UI:

```bash
streamlit run app.py
```

Alternatively, run the demo runner that processes a few claims:

```bash
python main.py
```

## Environment variables

Create a `.env` (or export these in your shell) with at minimum the following if you want LLM-backed behavior:

- `AZURE_OPENAI_API_KEY` — your Azure OpenAI key
- `AZURE_OPENAI_ENDPOINT` — your Azure endpoint (e.g. `https://...`)
- `DEPLOYMENT_NAME` — optional LLM deployment name
- `EMAIL_HITL_TO` — optional email address used by the HITL notification node

If these are not set, the code may fall back to non-LLM behavior or raise errors when calling the LLM.

## Project layout

- `app.py` — Streamlit web UI
- `main.py` — tiny runner that processes example claims from `data/`
- `processing.py` — batch processing, anomaly scoring, and the `process_claims()` API used by the app
- `agents.py` — policy/fraud/evidence/decision agent implementations
- `state_and_policy.py` — helper utilities to configure LLMs, retrieval, and the `ClaimState` type (see code)
- `graph.py` — LangGraph graph definition used to wire the agents together
- `notifications_mcp_client.py` — (optional) helper to send HITL emails
- `data/` — example CSVs and policy PDF used by the demo
- `requirements.txt` — Python dependencies

## Example usage (programmatic)

You can call the public API directly from Python:

```python
import pandas as pd
from processing import process_claims

df = pd.read_csv("data/warranty_claims.csv")
results = process_claims(df)
print(results.head())
```

The Streamlit app uses the same `process_claims()` function and exposes a UI for reviewing and overriding decisions.

## Data & privacy

- The repository contains small demo data under `data/` for illustration. Do not commit production data or secrets.
- If your CSVs are large or contain PII, keep them out of version control (add to `.gitignore`).

