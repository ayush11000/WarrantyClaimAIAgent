import os
from typing import TypedDict, List, Literal, Optional, Dict, Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# -----------------------------
# 1. State definition
# -----------------------------


class ClaimState(TypedDict):
    # Raw claim (one row from the CSV)
    claim: Dict[str, Any]

    # Agent outputs
    policy_check_summary: Optional[str]
    policy_coverage: Optional[Literal["covered", "not_covered", "unclear"]]
    policy_context: Optional[str]  # retrieved policy snippets

    fraud_score: Optional[float]  # 0–100
    fraud_reasons: List[str]

    evidence_summary: Optional[str]

    decision: Optional[Literal["approve", "decline", "escalate_hitl"]]
    decision_rationale: Optional[str]
    decision_confidence: Optional[float]

    # Anomaly / risk layer
    anomaly_score: Optional[float]  # avg z-score across numeric features
    risk_bucket: Optional[Literal["low", "medium", "high"]]
    anomaly_features: Dict[str, float]  # per-field z-scores

    # HITL fields
    hitl_required: bool
    hitl_notes: Optional[str]

    # Log of what each agent did
    trace: List[str]


# -----------------------------
# 2. LLM, embeddings & policy loading
# -----------------------------


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0,
    )


POLICY_TEXT: Optional[str] = None  # Simple module-level cache
EMBEDDINGS: Optional[OpenAIEmbeddings] = None
POLICY_RETRIEVER = None  # lazy-initialized retriever


def get_embeddings() -> OpenAIEmbeddings:
    global EMBEDDINGS
    if EMBEDDINGS is None:
        EMBEDDINGS = OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="text-embedding-3-small",
        )
    return EMBEDDINGS


def load_policy_text() -> str:
    """
    Loads the company warranty policy PDF and returns plain text.
    """
    pdf_path = os.path.join(
        os.path.dirname(__file__), "data", "AutoDrive_Warranty_Policy_2025.pdf"
    )
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    return "\n\n".join(d.page_content for d in docs)


def get_policy_text() -> str:
    global POLICY_TEXT
    if POLICY_TEXT is None:
        POLICY_TEXT = load_policy_text()
    return POLICY_TEXT


def get_policy_retriever():
    """
    Build a small vector DB (Chroma) over the policy text and return a retriever.
    Uses OpenAI embeddings. Built lazily and reused across claims.
    """
    global POLICY_RETRIEVER
    if POLICY_RETRIEVER is not None:
        return POLICY_RETRIEVER

    policy_text = get_policy_text()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    docs = splitter.create_documents([policy_text])

    vs = Chroma.from_documents(docs, get_embeddings())
    POLICY_RETRIEVER = vs.as_retriever(search_kwargs={"k": 4})
    return POLICY_RETRIEVER
