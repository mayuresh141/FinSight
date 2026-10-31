from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Tuple

from models import CardProfiles, Transaction
from tools import analysis_as_dict, analyze_spending, calculate_score, find_missed_rewards
from validators import redact_pii


SYSTEM_PROMPT = """You are FinSight, an evidence-grounded financial assistant.
Choose the smallest relevant tool for the user's question:
- analyze_spending for spending totals and category breakdowns
- find_missed_rewards for cashback opportunities
- calculate_score for the rewards optimization score
You may call more than one tool when the user asks for a combined analysis.
Never invent transactions, cards, rates, or financial figures. Explain only values
returned by tools. Card rates are synthetic user-provided rules, not real product claims.
If the user asks about a card not in the uploaded profiles, say it is unavailable and
ask them to add its profile; do not estimate its benefits.
"""


def missing_requested_card_response(question: str, profiles: CardProfiles):
    """Reject a named card that is not present in the uploaded profiles."""
    known_names = {card.name.lower() for card in profiles.cards}
    known_ids = {card.id.lower() for card in profiles.cards}
    match = re.search(r"using\s+(?:my\s+)?([^?!.]+)", question, flags=re.IGNORECASE)
    if not match:
        return None
    requested = match.group(1).strip().lower()
    if requested in known_names or requested in known_ids:
        return None
    if any(token in requested for token in ("card", "sapphire", "reserve", "cash", "visa", "mastercard", "amex")):
        return (
            "I cannot calculate that comparison because '%s' is not present in the uploaded card profiles. "
            "Please add its synthetic reward rules to cards.json; I will not use external card benefits "
            "or invent a rate." % match.group(1).strip()
        )
    return None


def pii_request_response(question: str):
    """Refuse direct requests to reveal sensitive identifiers from uploaded data."""
    lower = question.lower()
    sensitive_terms = (
        "ssn", "social security", "email address", "phone number", "telephone number",
        "account number", "bank account", "card number", "credit card number",
    )
    request_terms = ("what is", "show", "tell me", "give me", "reveal", "list", "find")
    if any(term in lower for term in sensitive_terms) and any(term in lower for term in request_terms):
        return (
            "I cannot reveal or retrieve personally identifiable information such as SSNs, contact details, "
            "or account/card numbers. I can still analyze spending and cashback opportunities without exposing it."
        )
    return None


def fallback_response(question: str, result: Dict[str, Any]) -> str:
    """Provide a transparent deterministic response when Groq is unavailable."""
    lower = question.lower()
    lines = ["Groq is not configured, so this is the deterministic analysis result."]
    if "score" in lower or "optimization" in lower:
        score = result.get("score")
        if score is None:
            lines.append(result.get("explanation", "The score is unavailable."))
        else:
            lines.append("Rewards Optimization Score: %s/100." % score)
            lines.append(result.get("explanation", ""))
        lines.append("Actual estimated cashback: $%s." % result.get("actual_estimated_cashback"))
        lines.append("Maximum estimated cashback: $%s." % result.get("maximum_estimated_cashback"))
        return "\n".join(line for line in lines if line)
    if "spend" in lower or "category" in lower or "month" in lower:
        lines.append("Total eligible purchase spending: $%s." % result.get("total_purchase_spending"))
        lines.append("Spending by category:")
        for category, amount in result.get("spending_by_category", {}).items():
            lines.append("- %s: $%s" % (category, amount))
        return "\n".join(lines)

    lines.append("Potential missed cashback: $%s." % result.get("potential_missed_cashback"))
    findings = result.get("findings", [])
    if findings:
        lines.append("Top evidence:")
        for finding in findings[:5]:
            lines.append(
                "- %s (%s): use %s instead of %s for an additional $%s [%s]." % (
                    finding["merchant"], finding["transaction_id"],
                    finding["recommended_alternative_card"], finding["card_actually_used"],
                    finding["potential_additional_cashback"], finding["supporting_reward_rule_id"],
                )
            )
    else:
        lines.append("No missed opportunities were found in the eligible transactions.")
    return "\n".join(lines)


def _tool_schema(name: str, description: str) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    }


def _execute_tool(name: str, transactions: List[Transaction], profiles: CardProfiles):
    if name == "analyze_spending":
        return analyze_spending(transactions)
    if name == "find_missed_rewards":
        return find_missed_rewards(transactions, profiles)
    if name == "calculate_score":
        return calculate_score(find_missed_rewards(transactions, profiles))
    raise ValueError("Unsupported tool requested: %s" % name)


def _fallback_for_question(question: str, transactions: List[Transaction], profiles: CardProfiles):
    lower = question.lower()
    if "score" in lower or "optimization" in lower:
        return calculate_score(find_missed_rewards(transactions, profiles)), "calculate_score"
    if "spend" in lower or "category" in lower or "month" in lower:
        return analyze_spending(transactions), "analyze_spending"
    return find_missed_rewards(transactions, profiles), "find_missed_rewards"


def run_agent(question: str, transactions: List[Transaction], profiles: CardProfiles) -> Tuple[str, List[str], Dict[str, Any]]:
    pii_response = pii_request_response(question)
    if pii_response:
        return pii_response, ["Guardrail: refused direct PII retrieval request"], {}

    missing_card_response = missing_requested_card_response(question, profiles)
    if missing_card_response:
        return redact_pii(missing_card_response), ["Guardrail: rejected unsupported card comparison"], {}

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        result, tool_name = _fallback_for_question(question, transactions, profiles)
        result_dict = redact_pii(analysis_as_dict(result))
        return fallback_response(question, result_dict), [tool_name + ": executed deterministic tool", "Groq agent: skipped (GROQ_API_KEY is not set)"], result_dict

    try:
        from groq import Groq
    except ImportError:
        result, tool_name = _fallback_for_question(question, transactions, profiles)
        result_dict = redact_pii(analysis_as_dict(result))
        return fallback_response(question, result_dict), [tool_name + ": executed deterministic tool", "Groq agent: skipped (groq package is not installed)"], result_dict

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    tools = [
        _tool_schema("analyze_spending", "Summarize eligible purchase spending by category."),
        _tool_schema("find_missed_rewards", "Find cashback opportunities using only uploaded card rules."),
        _tool_schema("calculate_score", "Calculate the rewards optimization score from verified cashback results."),
    ]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    trace: List[str] = []
    last_result: Dict[str, Any] = {}
    try:
        # Allow a short dependency chain plus one final answer turn.
        for _ in range(6):
            completion = client.chat.completions.create(
                model=model, messages=messages, tools=tools, tool_choice="auto", temperature=0
            )
            message = completion.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                if not trace:
                    trace.append("LLM selected no tool; no financial figures were generated")
                return message.content or fallback_response(question, last_result), trace, last_result

            names = [call.function.name for call in tool_calls]
            trace.append("LLM selected tool: " + ", ".join(names))
            messages.append({"role": "assistant", "content": message.content or "", "tool_calls": [
                {"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}}
                for call in tool_calls
            ]})
            for call in tool_calls:
                result = _execute_tool(call.function.name, transactions, profiles)
                last_result = redact_pii(analysis_as_dict(result))
                trace.append(call.function.name + ": executed deterministic tool")
                messages.append({"role": "tool", "tool_call_id": call.id, "name": call.function.name, "content": json.dumps(last_result, default=str)})
        raise RuntimeError("Tool-calling loop exceeded six rounds")
    except Exception as exc:
        result, tool_name = _fallback_for_question(question, transactions, profiles)
        result_dict = redact_pii(analysis_as_dict(result))
        trace.append("Groq agent error: %s" % exc)
        trace.append(tool_name + ": executed deterministic fallback tool")
        return fallback_response(question, result_dict), trace, result_dict

