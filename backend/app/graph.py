"""
LangGraph workflow — wires agents into a runnable pipeline.

This is where the three agents become a single workflow.
We define:
  1. The state type (what data flows through)
  2. The nodes (our three agent functions)
  3. The edges (which node runs after which)

The result is a compiled "graph" that you can invoke with an
initial state and it runs all three agents in sequence,
passing state between them automatically.

Think of this file as the wiring diagram — each agent is a
component, and this file connects the wires between them.
"""

from langgraph.graph import StateGraph, START, END
from app.state import AgentState
from app.agents.triage import triage_node
from app.agents.research import research_node
from app.agents.resolution import resolution_node
from app.agents.guardrails_node import guardrails_node


def build_graph():
    """Build and compile the agent workflow graph.

    Returns a compiled graph that can be invoked with:
        result = await graph.ainvoke({"customer_name": ..., "message": ...})
    """

    builder = StateGraph(AgentState)

    # Add nodes — now 4 nodes instead of 3
    builder.add_node("triage", triage_node)
    builder.add_node("research", research_node)
    builder.add_node("resolution", resolution_node)
    builder.add_node("guardrails", guardrails_node)

    # Define the flow:
    # START → triage → research → resolution → guardrails → END
    builder.add_edge(START, "triage")
    builder.add_edge("triage", "research")
    builder.add_edge("research", "resolution")
    builder.add_edge("resolution", "guardrails")   # check before finishing
    builder.add_edge("guardrails", END)

    graph = builder.compile()

    return graph


# Create a single graph instance used by the API
support_graph = build_graph()