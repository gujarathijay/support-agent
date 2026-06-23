"""
Memory module — gives agents the ability to remember past interactions.

How it works:
  1. After a ticket is resolved, we store a summary in ChromaDB
  2. When a new ticket comes in, agents search for relevant past tickets
  3. ChromaDB finds matches by MEANING, not keywords
     → "double charged" finds past tickets about "billed twice"

ChromaDB stores:
  - The text (a summary of the interaction)
  - Metadata (customer_id, category, priority, timestamp)
  - An embedding (a list of numbers representing the text's meaning)

When you search, ChromaDB converts your query to an embedding,
then finds stored items whose embeddings are closest in meaning.

The data persists to disk in the ./chroma_data directory, so
memories survive server restarts.
"""

import chromadb
from datetime import datetime


# Create a persistent ChromaDB client — data saved to disk
client = chromadb.PersistentClient(path="./chroma_data")

# Get or create our collection — like a table in a database
# ChromaDB automatically handles embedding generation
collection = client.get_or_create_collection(
    name="ticket_memories",
    metadata={"description": "Past support ticket interactions"},
)


def store_memory(
    customer_id: str,
    customer_name: str,
    category: str,
    priority: str,
    summary: str,
    resolution: str,
) -> str:
    """Store a completed ticket interaction as a memory.

    Called after a ticket is resolved. Creates a concise summary
    and stores it in ChromaDB with metadata for filtering.

    Returns the memory ID for reference.
    """

    # Create a rich text summary that captures the key details
    memory_text = (
        f"Customer {customer_name} ({customer_id}) had a {priority} priority "
        f"{category} issue: {summary}. "
        f"Resolution: {resolution}"
    )

    # Generate a unique ID for this memory
    memory_id = f"mem_{customer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Store in ChromaDB
    # - documents: the text to embed and search
    # - metadatas: structured data for filtering
    # - ids: unique identifier
    collection.add(
        documents=[memory_text],
        metadatas=[{
            "customer_id": customer_id,
            "customer_name": customer_name,
            "category": category,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
        }],
        ids=[memory_id],
    )

    return memory_id


def search_memory(
    query: str,
    customer_id: str | None = None,
    limit: int = 3,
) -> list[dict]:
    """Search past interactions by meaning.

    Args:
        query: What to search for (e.g. "billing issue double charge")
        customer_id: Optional — filter to a specific customer's history
        limit: Maximum number of results to return

    Returns a list of dicts with the memory text, metadata, and
    a relevance score (lower distance = more relevant).
    """

    # Don't search if the collection is empty
    if collection.count() == 0:
        return []

    # Build the query — optionally filter by customer
    query_params = {
        "query_texts": [query],
        "n_results": min(limit, collection.count()),
    }

    if customer_id:
        query_params["where"] = {"customer_id": customer_id}

    results = collection.query(**query_params)

    # Format results into clean dicts
    memories = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            memories.append({
                "text": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })

    return memories


def get_customer_history(customer_id: str, limit: int = 5) -> list[dict]:
    """Get all past interactions for a specific customer.

    Unlike search_memory, this doesn't need a query — it just
    returns everything we know about this customer, sorted by time.
    """

    if collection.count() == 0:
        return []

    try:
        results = collection.get(
            where={"customer_id": customer_id},
            limit=limit,
        )
    except Exception:
        return []

    memories = []
    if results["documents"]:
        for i, doc in enumerate(results["documents"]):
            memories.append({
                "text": doc,
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
            })

    return memories


def clear_all_memories():
    """Delete all memories. Useful for testing."""
    client.delete_collection("ticket_memories")
    # Recreate the empty collection
    global collection
    collection = client.get_or_create_collection(
        name="ticket_memories",
        metadata={"description": "Past support ticket interactions"},
    )