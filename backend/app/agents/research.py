"""
Research Agent — now with REAL tool calling.

What changed from Phase 2:
  - The LLM has tools bound to it (lookup_order, search_knowledge_base)
  - When Claude wants to call a tool, WE execute the function
  - We send the result back to Claude
  - Claude uses the real data in its research findings

The tool calling loop:
  1. Call Claude with tools available
  2. If Claude returns tool_calls → execute each tool
  3. Send results back to Claude
  4. Repeat until Claude responds with text (no more tool calls)
  5. Return the text as research_findings
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, ToolMessage
from app.config import settings
from app.state import AgentState
from app.tools.support_tools import all_tools

# Create the LLM and BIND the tools to it
# bind_tools() tells Claude "these tools exist and you can call them"
llm = ChatAnthropic(
    model=settings.model_name,
    api_key=settings.anthropic_api_key,
    max_tokens=settings.max_tokens,
)
llm_with_tools = llm.bind_tools(all_tools)

RESEARCH_PROMPT = """You are a customer support research specialist.

A ticket has been triaged. Your job is to research the issue by
looking up relevant data and policies using the tools available to you.

Ticket details:
- Customer: {customer_name}
- Customer ID: {customer_id}
- Category: {category}
- Priority: {priority}
- Sentiment: {sentiment}
- Summary: {summary}
- Original message: {message}

Instructions:
1. ALWAYS look up the customer's order history using their customer ID
2. ALWAYS search the knowledge base for relevant policies
3. ALWAYS search past tickets to check if this customer has contacted us before
4. Use the actual data from these lookups in your findings
5. If the customer has past interactions, note any patterns or prior resolutions
6. Summarize everything the resolution agent needs to draft a response

Do NOT make up data. Only use information from the tool results.
"""


async def research_node(state: AgentState) -> dict:
    """LangGraph node: research the ticket using real tools."""
    import time
    start = time.time()

    prompt = RESEARCH_PROMPT.format(
        customer_name=state["customer_name"],
        customer_id=state["customer_id"],
        message=state["message"],
        category=state.get("category", "general"),
        priority=state.get("priority", "medium"),
        sentiment=state.get("sentiment", "neutral"),
        summary=state.get("summary", "No summary available"),
    )

    messages = [HumanMessage(content=prompt)]
    tool_map = {t.name: t for t in all_tools}

    max_iterations = 5
    tools_called = []   # ← track every tool name Claude actually called
    for _ in range(max_iterations):

        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tools_called.append(tool_name)   # ← record it

            print(f"  [Research Agent] Calling tool: {tool_name}({tool_args})")

            tool_func = tool_map[tool_name]
            result = await tool_func.ainvoke(tool_args)

            tool_message = ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
            )
            messages.append(tool_message)

    elapsed = time.time() - start
    print(f"  [Research] Done — {len(tools_called)} tool calls ({elapsed:.1f}s)")

    return {
        "research_findings": response.content,
        "tools_called": tools_called,   # ← now part of shared state
    }