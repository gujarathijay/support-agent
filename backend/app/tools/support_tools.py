"""
Support tools — real functions that agents can execute.

These are the "hands" of our agents. Each tool is a Python function
decorated with @tool, which tells LangChain:
  1. The function's name (used by Claude to call it)
  2. The description (Claude reads this to decide WHEN to use it)
  3. The argument schema (what inputs Claude must provide)

When Claude says "I want to call lookup_order(customer_id='CUST-001')",
our code runs this actual function and sends the result back.

The @tool decorator converts a regular Python function into a
LangChain Tool object that can be bound to an LLM.
"""

import json
from langchain_core.tools import tool
from app.data.mock_data import ORDERS, KNOWLEDGE_BASE


@tool
def lookup_order(customer_id: str) -> str:
    """Look up a customer's account and order history by their customer ID.

    Use this tool when you need to find information about a customer's
    orders, billing history, subscription plan, or payment details.
    Returns the customer's profile and all their orders.
    """

    # In production: db.query("SELECT * FROM orders WHERE customer_id = ?", customer_id)
    customer = ORDERS.get(customer_id)

    if not customer:
        return json.dumps({
            "error": f"No customer found with ID: {customer_id}",
            "suggestion": "Verify the customer ID and try again"
        })

    return json.dumps(customer, indent=2)


@tool
def search_knowledge_base(query: str) -> str:
    """Search the support knowledge base for relevant articles and policies.

    Use this tool when you need to find company policies, procedures,
    troubleshooting guides, or standard operating procedures related
    to a customer's issue. Provide a search query describing what
    you're looking for.
    """

    # In production: this would be a vector similarity search
    # For now: simple keyword matching
    query_lower = query.lower()
    results = []

    for article in KNOWLEDGE_BASE:
        # Check if query terms appear in title, category, or content
        searchable = f"{article['title']} {article['category']} {article['content']}".lower()
        # Count how many query words match
        query_words = query_lower.split()
        matches = sum(1 for word in query_words if word in searchable)

        if matches > 0:
            results.append({
                "id": article["id"],
                "title": article["title"],
                "category": article["category"],
                "content": article["content"],
                "relevance": matches,
            })

    # Sort by relevance (most matching words first)
    results.sort(key=lambda x: x["relevance"], reverse=True)

    if not results:
        return json.dumps({
            "message": "No relevant articles found",
            "suggestion": "Try different search terms"
        })

    # Return top 3 most relevant articles
    return json.dumps(results[:3], indent=2)


@tool
def search_past_tickets(customer_id: str, query: str) -> str:
    """Search for past support interactions with a customer.

    Use this tool to check if the customer has contacted support before
    and what happened. This helps you understand their history and
    avoid repeating solutions that didn't work.
    """
    from app.memory import search_memory, get_customer_history

    # First get any history for this specific customer
    history = get_customer_history(customer_id, limit=3)

    # Also search by topic in case other customers had similar issues
    similar = search_memory(query, limit=2)

    # Log what we found so you can see in the server terminal
    print(f"    → Memory: {len(history)} past interactions for {customer_id}")
    print(f"    → Memory: {len(similar)} similar tickets found")

    results = {
        "customer_history": [m["text"] for m in history] if history else ["No past interactions found for this customer"],
        "similar_tickets": [m["text"] for m in similar] if similar else ["No similar past tickets found"],
    }

    return json.dumps(results, indent=2)


# List of all tools — imported by the research agent
all_tools = [lookup_order, search_knowledge_base, search_past_tickets]