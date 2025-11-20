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

## Development notes & next steps

- Consider adding a `.env.example` with placeholder names but not secrets.
- Add automated tests for critical graph nodes and a CI workflow (GitHub Actions) to run linting and tests.
- Consider adding a small Dockerfile for reproducible runtimes.

## License

MIT

---

If you want, I can also:
- rename `reqirements.txt` → `requirements.txt` if present,
- add a `.env.example`,
- add a minimal GitHub Actions workflow, or
- create a `Dockerfile` for reproducible runs.

````
# Warranty Fraud Detector (Langgraph Tutorial)

<img width="1910" height="942" alt="Screenshot 2025-10-03 103030" src="https://github.com/user-attachments/assets/876111df-6741-43b3-b4af-d0cdeaba4558" />


A small demo project that uses LangGraph + an Azure OpenAI-backed LLM to validate warranty claims, score fraud likelihood, collect evidence, and make an adjudication decision. The project includes a Streamlit app (`app.py`) and a demonstration notebook (`agent.ipynb`).

Purpose: This repository is provided for study and educational purposes only. You are free to use, adapt, and experiment with the code for learning, demonstrations, and research. It is not intended as a production-ready system. If you plan to use this code with real data or in production, implement appropriate security, privacy, and compliance measures before doing so.

## What this project contains

- `app.py` - Streamlit application to interact with the claims pipeline.
- `agent.ipynb` - Jupyter notebook demonstrating the `StateGraph` implementation, LLM-driven agents, and a small demo run.
- `data/` - demo data and the policy PDF used by the agents:
  - `warranty_claims.csv` - sample claims data
  - `AutoDrive_Warranty_Policy_2025.pdf` - policy manual used for policy checks
- `reqirements.txt` - Python dependencies for the project (note the filename is intentionally present in the repository as `reqirements.txt`).

## Prerequisites

- Python 3.10+ (project was developed with modern Python 3.x)
- Streamlit (installed via the requirements file)
- An Azure OpenAI deployment (optional but required for the LLM-driven behavior)
- A local virtual environment (recommended)
- Windows (instructions below use `cmd.exe`)

Note about the package manager: you mentioned using the UV Python package manager. The README below shows standard `python -m venv` + `pip` commands which will work even if you used `uv` to create the `.venv`. If you prefer `uv` workflows, use the same virtual environment activation commands you normally use with `uv`, then run the `pip install -r reqirements.txt` step.

## Setup (Windows, cmd.exe)

1. Open a `cmd.exe` terminal in the project root:

2. Create a virtual environment (if you don't already have one):

```cmd
python -m venv .venv
```

3. Activate the virtual environment:

```cmd
.venv\Scripts\activate
```

4. Install dependencies from the repository's requirements file:

```cmd
pip install --upgrade pip
pip install -r reqirements.txt
```

If you used the UV package manager to create/activate your environment already, skip steps 2–3 and simply install dependencies while your venv is active.

## Environment variables

This project expects sensitive keys to be provided via a `.env` file (the notebook calls `load_dotenv()`), or via environment variables. Create a `.env` file in the project root with the following keys filled in:

```
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-azure-endpoint
# Optional: the LLM deployment name used in the notebook/app
DEPLOYMENT_NAME=gpt-4o
```

Make sure your Azure deployment name, key and endpoint match what you use in the notebook/app. Without valid keys, the LLM calls will fail and the notebook/app will fall back to rule-based logic (if implemented).

## Run the Streamlit app

With the virtual environment active, run:

```cmd
streamlit run app.py
```

This will start the Streamlit server and open a browser tab where you can interact with the claims adjudication UI.

## Run the demo notebook

Open `agent.ipynb` using Jupyter or VS Code's notebook interface. The notebook contains a small demo that:

- loads `data/warranty_claims.csv` (3-row demo dataset),
- loads and concatenates the policy PDF, and
- runs each claim through the LangGraph `StateGraph` pipeline.

Ensure your virtual environment is active and the `.env` variables are set so the notebook can call the Azure LLM.

## Output

- The Streamlit app provides interactive evaluation of claims.
- The notebook writes a small `results_df` DataFrame (and you can uncomment the `results_df.to_csv("demo_claims_results.csv", index=False)` line to save CSV output).

## Troubleshooting

- If Streamlit fails to run: confirm the virtual environment is active and that `streamlit` is installed.
- If the LLM calls fail: check your `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT`. Inspect the notebook/app logs for helpful error traces.
- If you see `ModuleNotFoundError` for packages referenced in the notebook, re-run `pip install -r reqirements.txt` and confirm the correct Python interpreter/venv is active.

## Notes & next steps

- The project is a tutorial/demo. For production use you should add robust error handling, rate limiting, and secrets management (do not store API keys in plaintext).
- Consider renaming `reqirements.txt` to `requirements.txt` to match common conventions (remember to update any scripts that refer to the filename).

---

If you'd like, I can also:

- rename `reqirements.txt` to `requirements.txt` and update the README accordingly,
- add a short example `.env.example` file to the repo, or
- add a minimal Dockerfile or GitHub Actions workflow for reproducible runs.

Let me know which of those you'd like me to do next.

License: MIT (feel free to change)

Copyright © 2025 AaiTech. All rights reserved.

Owner: Sandesh Hase
