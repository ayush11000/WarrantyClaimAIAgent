from langgraph.graph import StateGraph, END

from state_and_policy import ClaimState
from agents import (
    policy_check_agent,
    fraud_scoring_agent,
    evidence_agent,
    decision_agent,
    hitl_review_node,
)


# -----------------------------
# 4. Graph wiring
# -----------------------------


def build_graph():
    graph = StateGraph(ClaimState)

    # Register nodes
    graph.add_node("policy_check_agent", policy_check_agent)
    graph.add_node("fraud_scoring_agent", fraud_scoring_agent)
    graph.add_node("evidence_agent", evidence_agent)
    graph.add_node("decision_agent", decision_agent)
    graph.add_node("hitl_review_node", hitl_review_node)

    # Start → policy_check_agent
    graph.set_entry_point("policy_check_agent")

    # Linear flow between main agents
    graph.add_edge("policy_check_agent", "fraud_scoring_agent")
    graph.add_edge("fraud_scoring_agent", "evidence_agent")
    graph.add_edge("evidence_agent", "decision_agent")

    # Conditional after decision_agent → either hitl_review_node or END
    def route_after_decision(state: ClaimState):
        decision = state.get("decision", "escalate_hitl")
        if decision == "escalate_hitl":
            return "hitl_review_node"
        else:
            return END

    graph.add_conditional_edges(
        "decision_agent",
        route_after_decision,
        {
            "hitl_review_node": "hitl_review_node",
            END: END,
        },
    )

    # hitl_review_node → END
    graph.add_edge("hitl_review_node", END)

    return graph.compile()


COMPILED_GRAPH = build_graph()
