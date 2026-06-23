"""
Eval scorers — measure how well the agent performs.

Each scorer takes the agent's output and returns a score between
0.0 and 1.0. Different scorers measure different things:

  - Triage accuracy: did it classify correctly? (exact match)
  - Guardrail compliance: is the response safe? (heuristic)
  - Response quality: is the response good? (LLM-as-judge)

Scores are combined into an overall quality metric that Braintrust
tracks over time. When you change a prompt or add a feature, you
re-run evals and compare scores to make sure nothing got worse.
"""

import os
import re


def score_triage_accuracy(output: dict, expected: dict) -> dict:
    """Score triage classification accuracy.

    Compares the agent's category, priority, and sentiment against
    the expected values. Returns individual scores and an average.

    Score: 1.0 = exact match, 0.0 = wrong
    """
    scores = {}

    # Category match
    scores["category_match"] = 1.0 if output.get("category") == expected.get("category") else 0.0

    # Priority match (partial credit for being one level off)
    priority_levels = ["low", "medium", "high", "urgent"]
    out_priority = output.get("priority", "medium")
    exp_priority = expected.get("priority", "medium")

    if out_priority == exp_priority:
        scores["priority_match"] = 1.0
    elif out_priority in priority_levels and exp_priority in priority_levels:
        diff = abs(priority_levels.index(out_priority) - priority_levels.index(exp_priority))
        scores["priority_match"] = max(0, 1.0 - (diff * 0.33))  # partial credit
    else:
        scores["priority_match"] = 0.0

    # Sentiment match
    scores["sentiment_match"] = 1.0 if output.get("sentiment") == expected.get("sentiment") else 0.0

    # Overall triage score (average of all three)
    scores["triage_overall"] = sum(scores.values()) / len(scores)

    return scores


def score_guardrail_compliance(output: dict) -> dict:
    """Score whether the response passes guardrail checks.

    Runs our existing guardrail checks on the draft response.
    No expected values needed — this is a safety check.
    """
    from app.guardrails import run_all_guardrails

    draft = output.get("draft_response", "")
    if not draft:
        return {"guardrail_compliance": 0.0}

    result = run_all_guardrails(draft)

    # Score based on severity of violations
    high_violations = sum(1 for v in result["violations"] if v["severity"] == "high")
    medium_violations = sum(1 for v in result["violations"] if v["severity"] == "medium")

    # High violations = 0 score, medium violations = partial deduction
    if high_violations > 0:
        score = 0.0
    elif medium_violations > 0:
        score = max(0.3, 1.0 - (medium_violations * 0.2))
    else:
        score = 1.0

    return {
        "guardrail_compliance": score,
        "high_violations": high_violations,
        "medium_violations": medium_violations,
    }


def score_tool_usage(output: dict, expected_tools: list[str] | None = None) -> dict:
    """Score whether the agent called the tools it was supposed to.

    This checks the AGENT'S PROCESS, not just its final answer.
    A response can look perfect but be based on guessed data if
    the agent skipped looking up the actual order/policy.

    Default expectation: every ticket should look up order history
    AND search the knowledge base. Skipping either is a process failure
    even if the final text happens to look fine.
    """
    if expected_tools is None:
        expected_tools = ["lookup_order", "search_knowledge_base"]

    tools_called = output.get("tools_called", []) or []
    tools_called_set = set(tools_called)

    # Did it call each expected tool at least once?
    called_expected = [t for t in expected_tools if t in tools_called_set]
    missing = [t for t in expected_tools if t not in tools_called_set]

    coverage = len(called_expected) / len(expected_tools) if expected_tools else 1.0

    return {
        "tool_usage_coverage": coverage,
        "tools_called": tools_called,
        "tools_missing": missing,
    }


def score_response_heuristics(output: dict, expected: dict) -> dict:
    """Score response quality using rule-based heuristics.

    These are fast, deterministic checks that don't require an LLM.
    Good for catching basic quality issues.
    """
    draft = output.get("draft_response", "")
    scores = {}

    # 1. Does it use the customer's name? (personalization)
    customer_name = output.get("customer_name", "").split()[0]  # first name
    scores["uses_customer_name"] = 1.0 if customer_name.lower() in draft.lower() else 0.0

    # 2. Is it a reasonable length? (not too short, not too long)
    word_count = len(draft.split())
    if 50 <= word_count <= 400:
        scores["appropriate_length"] = 1.0
    elif 30 <= word_count < 50 or 400 < word_count <= 600:
        scores["appropriate_length"] = 0.5
    else:
        scores["appropriate_length"] = 0.0

    # 3. Does it contain an apology for angry/frustrated customers?
    sentiment = output.get("sentiment", "neutral")
    if sentiment in ("angry", "frustrated"):
        apology_words = ["apologize", "sorry", "apology", "understand your frustration"]
        has_apology = any(word in draft.lower() for word in apology_words)
        scores["empathy_match"] = 1.0 if has_apology else 0.0
    else:
        scores["empathy_match"] = 1.0  # not needed for neutral/positive

    # 4. Does it mention next steps or a solution?
    action_words = ["refund", "process", "investigate", "fix", "resolve",
                    "follow up", "escalat", "credit", "team", "update"]
    has_action = any(word in draft.lower() for word in action_words)
    scores["contains_action"] = 1.0 if has_action else 0.0

    # Overall heuristic score
    scores["heuristic_overall"] = sum(scores.values()) / len(scores)

    return scores


def score_response_llm_judge(output: dict, expected: dict) -> dict:
    """Score response quality using an LLM as a judge.

    This sends the draft response to Claude and asks it to rate
    quality on multiple dimensions. More nuanced than heuristics
    but costs an API call per evaluation.

    Only run this scorer when you have an API key available.
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"llm_judge_overall": None, "note": "No API key, skipping LLM judge"}

    client = anthropic.Anthropic(api_key=api_key)

    draft = output.get("draft_response", "")
    category = output.get("category", "")
    sentiment = output.get("sentiment", "")
    message = output.get("message", "")

    prompt = f"""Rate this customer support response on a scale of 1-5 for each dimension.

Customer's original message: {message}
Ticket category: {category}
Customer sentiment: {sentiment}

Agent's draft response:
{draft}

Rate each dimension (1=poor, 5=excellent):
EMPATHY: Does it acknowledge the customer's feelings appropriately?
ACCURACY: Does it address the actual issue mentioned?
ACTIONABILITY: Does it provide clear next steps or a solution?
PROFESSIONALISM: Is the tone professional and appropriate?
COMPLETENESS: Does it fully address the customer's concerns?

Respond with ONLY the scores in this exact format:
EMPATHY: <1-5>
ACCURACY: <1-5>
ACTIONABILITY: <1-5>
PROFESSIONALISM: <1-5>
COMPLETENESS: <1-5>"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        scores = {}

        for line in text.strip().split("\n"):
            for dim in ["EMPATHY", "ACCURACY", "ACTIONABILITY", "PROFESSIONALISM", "COMPLETENESS"]:
                if line.upper().startswith(dim):
                    try:
                        val = int(re.search(r'(\d)', line.split(":")[-1]).group(1))
                        scores[dim.lower()] = val / 5.0  # normalize to 0-1
                    except (AttributeError, ValueError):
                        pass

        if scores:
            scores["llm_judge_overall"] = sum(scores.values()) / len(scores)
        else:
            scores["llm_judge_overall"] = None

        return scores

    except Exception as e:
        return {"llm_judge_overall": None, "error": str(e)}