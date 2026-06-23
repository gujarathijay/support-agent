"""
Eval runner — runs evaluations using Braintrust.

Usage:
  # Run with Braintrust (needs BRAINTRUST_API_KEY):
  python -m evals.run_evals

  # Run locally without Braintrust (prints results to terminal):
  python -m evals.run_evals --local

What this does:
  1. Loads the test dataset (8 labeled examples)
  2. Sends each ticket through the full workflow
  3. Scores the output with all scorers
  4. Reports results (locally or to Braintrust dashboard)

Braintrust tracks results over time so you can compare:
  "Did my prompt change improve triage accuracy?"
  "Did adding guardrails break response quality?"
"""

import asyncio
import sys
import os
import time
import json
from dotenv import load_dotenv

# Load .env file (same one FastAPI uses)
load_dotenv()

# Add parent dir to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.dataset import EVAL_DATASET
from evals.scorers import (
    score_triage_accuracy,
    score_guardrail_compliance,
    score_response_heuristics,
    score_response_llm_judge,
    score_tool_usage,
)


async def run_single_eval(test_case: dict) -> dict:
    """Run a single test case through the full workflow.

    Returns the workflow output for scoring.
    """
    from app.graph import support_graph

    initial_state = {
        "customer_name": test_case["input"]["customer_name"],
        "customer_id": test_case["input"]["customer_id"],
        "message": test_case["input"]["message"],
    }

    result = await support_graph.ainvoke(initial_state)
    return result


def score_result(output: dict, expected: dict) -> dict:
    """Run all scorers on a single result and return combined scores."""
    all_scores = {}

    # Triage accuracy (fast, no LLM)
    all_scores.update(score_triage_accuracy(output, expected))

    # Tool usage — did the agent actually look things up? (fast, no LLM)
    all_scores.update(score_tool_usage(output))

    # Guardrail compliance (fast, no LLM)
    all_scores.update(score_guardrail_compliance(output))

    # Response heuristics (fast, no LLM)
    all_scores.update(score_response_heuristics(output, expected))

    # LLM judge (slow, costs money — skip with --no-judge flag)
    if "--no-judge" not in sys.argv:
        all_scores.update(score_response_llm_judge(output, expected))

    return all_scores


async def run_local():
    """Run evals locally and print results to terminal."""
    print("=" * 60)
    print("RUNNING EVALS (local mode)")
    print("=" * 60)

    all_scores = []
    total_start = time.time()

    for i, test_case in enumerate(EVAL_DATASET):
        name = test_case["input"]["customer_name"]
        print(f"\n[{i+1}/{len(EVAL_DATASET)}] {name}...")

        start = time.time()
        output = await run_single_eval(test_case)
        elapsed = time.time() - start

        scores = score_result(output, test_case["expected"])
        all_scores.append(scores)

        # Print key scores
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Category: {output.get('category')} (expected: {test_case['expected']['category']}) → {'✓' if scores.get('category_match') == 1.0 else '✗'}")
        print(f"  Priority: {output.get('priority')} (expected: {test_case['expected']['priority']}) → {scores.get('priority_match', 0):.2f}")
        print(f"  Sentiment: {output.get('sentiment')} (expected: {test_case['expected']['sentiment']}) → {'✓' if scores.get('sentiment_match') == 1.0 else '✗'}")
        print(f"  Tools called: {scores.get('tools_called', [])} → coverage {scores.get('tool_usage_coverage', 0):.2f}")
        if scores.get("tools_missing"):
            print(f"    Missing: {scores['tools_missing']}")
        print(f"  Guardrail: {scores.get('guardrail_compliance', 0):.2f}")
        print(f"  Heuristic: {scores.get('heuristic_overall', 0):.2f}")
        if scores.get("llm_judge_overall") is not None:
            print(f"  LLM Judge: {scores.get('llm_judge_overall', 0):.2f}")

    # Print summary
    total_time = time.time() - total_start
    print("\n" + "=" * 60)
    print("EVAL SUMMARY")
    print("=" * 60)

    # Calculate averages for each metric
    metrics = ["category_match", "priority_match", "sentiment_match",
               "triage_overall", "tool_usage_coverage", "guardrail_compliance", "heuristic_overall"]

    for metric in metrics:
        values = [s.get(metric, 0) for s in all_scores if s.get(metric) is not None]
        if values:
            avg = sum(values) / len(values)
            print(f"  {metric:25s}: {avg:.2f} ({avg*100:.0f}%)")

    # LLM judge if available
    judge_values = [s.get("llm_judge_overall") for s in all_scores if s.get("llm_judge_overall") is not None]
    if judge_values:
        avg = sum(judge_values) / len(judge_values)
        print(f"  {'llm_judge_overall':25s}: {avg:.2f} ({avg*100:.0f}%)")

    print(f"\n  Total time: {total_time:.1f}s")
    print(f"  Test cases: {len(EVAL_DATASET)}")
    print()


async def run_braintrust():
    """Run evals with Braintrust tracking."""
    import braintrust

    print("Running evals with Braintrust tracking...")

    eval_results = []

    for test_case in EVAL_DATASET:
        output = await run_single_eval(test_case)
        scores = score_result(output, test_case["expected"])

        # Braintrust only accepts numbers as scores
        # Move non-numeric data (lists like tools_called) to output
        numeric_scores = {k: v for k, v in scores.items() if isinstance(v, (int, float)) and v is not None}

        eval_results.append({
            "input": test_case["input"],
            "output": {
                "category": output.get("category"),
                "priority": output.get("priority"),
                "sentiment": output.get("sentiment"),
                "summary": output.get("summary"),
                "draft_response": output.get("draft_response", "")[:500],
                "tools_called": scores.get("tools_called", []),
                "tools_missing": scores.get("tools_missing", []),
            },
            "expected": test_case["expected"],
            "scores": numeric_scores,
        })

    # Log to Braintrust
    experiment = braintrust.init(
        project="support-resolution-agent",
        experiment="eval-run",
    )

    for result in eval_results:
        experiment.log(
            input=result["input"],
            output=result["output"],
            expected=result["expected"],
            scores=result["scores"],
        )

    summary = experiment.summarize()
    print(f"\nBraintrust experiment: {summary}")


async def main():
    if "--local" in sys.argv or not os.environ.get("BRAINTRUST_API_KEY"):
        if not os.environ.get("BRAINTRUST_API_KEY"):
            print("No BRAINTRUST_API_KEY found — running in local mode")
            print("Set BRAINTRUST_API_KEY to track results in Braintrust\n")
        await run_local()
    else:
        await run_braintrust()


if __name__ == "__main__":
    asyncio.run(main())