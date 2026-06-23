"""
Guardrail checks for the support resolution agent.

Each guardrail is a simple function that takes text and returns
a list of violations found. A violation is a dict with:
  - type: what kind of problem (e.g. "pii_email")
  - message: human-readable description
  - severity: "high" (must fix) or "medium" (should fix)

Design principles:
  1. Each check is independent — you can add/remove checks easily
  2. Checks are fast — no LLM calls, just regex and string matching
  3. False positives are better than missed violations
  4. High severity = block the response, medium = warn but allow

In production, you'd add: prompt injection detection, toxicity
scoring (using a classifier model), language detection, and
compliance checks specific to your industry.
"""

import re
from typing import Optional


def check_pii(text: str) -> list[dict]:
    """Check for personally identifiable information in the response.

    The agent should NEVER include customer PII in a response.
    Common leaks: the agent reads email/phone from order data
    and accidentally includes it in the draft.

    Checks for:
    - Email addresses (user@example.com)
    - Phone numbers (various formats)
    - SSN patterns (XXX-XX-XXXX)
    """
    violations = []

    # Email addresses
    emails = re.findall(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        text
    )
    # Filter out placeholder emails that the agent is SUPPOSED to use
    real_emails = [e for e in emails if not e.startswith("[") and "example.com" not in e]
    if real_emails:
        violations.append({
            "type": "pii_email",
            "message": f"Response contains email address(es): {', '.join(real_emails)}",
            "severity": "high",
        })

    # Phone numbers — matches formats like (555) 123-4567, 555-123-4567, +1234567890
    phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phones = re.findall(phone_pattern, text)
    if phones:
        violations.append({
            "type": "pii_phone",
            "message": f"Response contains phone number(s): {', '.join(phones)}",
            "severity": "high",
        })

    # SSN pattern — XXX-XX-XXXX
    ssns = re.findall(r'\b\d{3}-\d{2}-\d{4}\b', text)
    if ssns:
        violations.append({
            "type": "pii_ssn",
            "message": "Response contains SSN-like pattern",
            "severity": "high",
        })

    return violations


def check_refund_limit(text: str, max_refund: float = 500.0) -> list[dict]:
    """Check if the response promises a refund exceeding the agent's authority.

    From our knowledge base: "Maximum refund authority for support
    agents: $500. Amounts above $500 require manager approval."

    Scans for dollar amounts and flags any over the limit.
    """
    violations = []

    # Find all dollar amounts in the text — matches $29.99, $500, $1,000.00
    amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', text)

    for amount_str in amounts:
        # Parse the numeric value
        clean = amount_str.replace("$", "").replace(",", "")
        try:
            amount = float(clean)
            if amount > max_refund:
                violations.append({
                    "type": "refund_limit",
                    "message": f"Response mentions {amount_str} which exceeds agent refund limit of ${max_refund:.2f}",
                    "severity": "high",
                })
        except ValueError:
            continue

    return violations


def check_banned_phrases(text: str) -> list[dict]:
    """Check for phrases that create legal liability or false promises.

    Support agents should NEVER make absolute guarantees or legal
    commitments. These phrases are banned because:
    - "I guarantee" → creates a contractual obligation
    - "I promise" → personal commitment the company can't enforce
    - "we will definitely" → absolute commitment without certainty
    - "guaranteed" → same as above
    - "100%" → implies certainty that doesn't exist
    """
    violations = []

    banned = [
        ("i guarantee", "Legal liability — agents cannot make guarantees"),
        ("i promise", "Personal commitment — use 'I'll do my best' instead"),
        ("we will definitely", "Absolute commitment — use 'we'll work to' instead"),
        ("guaranteed", "Legal liability — avoid absolute guarantees"),
        ("100% sure", "False certainty — nothing is 100% certain"),
        ("you will certainly", "Absolute commitment — use 'you should' instead"),
        ("we promise", "Corporate commitment — requires legal approval"),
        ("legal action", "Legal topic — do not discuss, escalate to legal team"),
        ("sue", "Legal topic — do not discuss, escalate to legal team"),
        ("lawyer", "Legal topic — do not discuss, escalate to legal team"),
    ]

    text_lower = text.lower()

    for phrase, reason in banned:
        if phrase in text_lower:
            violations.append({
                "type": "banned_phrase",
                "message": f"Found banned phrase '{phrase}': {reason}",
                "severity": "medium",
            })

    return violations


def run_all_guardrails(text: str) -> dict:
    """Run all guardrail checks on a piece of text.

    Returns a dict with:
      - passed: True if no high-severity violations
      - violations: list of all violations found
      - summary: human-readable summary
    """
    all_violations = []
    all_violations.extend(check_pii(text))
    all_violations.extend(check_refund_limit(text))
    all_violations.extend(check_banned_phrases(text))

    high_severity = [v for v in all_violations if v["severity"] == "high"]
    passed = len(high_severity) == 0

    if not all_violations:
        summary = "All guardrail checks passed"
    else:
        high_count = len(high_severity)
        medium_count = len(all_violations) - high_count
        parts = []
        if high_count:
            parts.append(f"{high_count} high-severity")
        if medium_count:
            parts.append(f"{medium_count} medium-severity")
        summary = f"Found {', '.join(parts)} violation(s)"

    return {
        "passed": passed,
        "violations": all_violations,
        "summary": summary,
    }


def redact_pii(text: str) -> tuple[str, int]:
    """Auto-redact PII from text. Returns (cleaned_text, redaction_count).

    This runs AFTER detection. If check_pii found emails or phones,
    this function strips them out so the draft is safe by default.
    The human reviewer sees [EMAIL REDACTED] instead of the real data.
    """
    count = 0

    # Redact emails (but not placeholders like [email])
    def replace_email(match):
        email = match.group(0)
        if "example.com" in email:
            return email  # leave placeholder emails alone
        nonlocal count
        count += 1
        return "[EMAIL REDACTED]"

    text = re.sub(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        replace_email,
        text,
    )

    # Redact phone numbers
    def replace_phone(match):
        nonlocal count
        count += 1
        return "[PHONE REDACTED]"

    text = re.sub(
        r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        replace_phone,
        text,
    )

    # Redact SSN patterns
    def replace_ssn(match):
        nonlocal count
        count += 1
        return "[SSN REDACTED]"

    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', replace_ssn, text)

    return text, count