from __future__ import annotations

import os
import re
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Set

from agent import run_agent
from models import CardProfiles, Transaction


CASES = [
    {"name": "missed_rewards", "question": "Where did I miss cashback?", "expected_tool": "find_missed_rewards"},
    {"name": "score", "question": "What is my rewards optimization score?", "expected_tool": "calculate_score"},
]


def _currency_values(value: Any) -> Iterable[Decimal]:
    if isinstance(value, dict):
        for nested in value.values():
            yield from _currency_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _currency_values(nested)
    elif isinstance(value, (int, float, Decimal, str)):
        try:
            if isinstance(value, str) and not re.fullmatch(r"-?\d+(?:\.\d+)?", value.strip()):
                return
            yield Decimal(str(value)).quantize(Decimal("0.01"))
        except InvalidOperation:
            return


def _response_currency_values(response: str) -> Set[Decimal]:
    values = set()
    for match in re.findall(r"\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)", response):
        try:
            values.add(Decimal(match.replace(",", "")).quantize(Decimal("0.01")))
        except InvalidOperation:
            continue
    return values


def evaluate_response(response: str, trace: List[str], result: Dict[str, Any], transactions: List[Transaction], profiles: CardProfiles, expected_tool: str) -> Dict[str, Any]:
    known_transaction_ids = {transaction.transaction_id for transaction in transactions}
    known_rule_ids = {card.base_rule_id for card in profiles.cards}
    for card in profiles.cards:
        known_rule_ids.update(rule.rule_id for rule in card.categories.values())

    referenced_transactions = set(re.findall(r"\bTX\d+\b", response))
    referenced_rules = set(re.findall(r"\bRULE-[A-Z0-9-]+\b", response))
    evidence_valid = referenced_transactions <= known_transaction_ids and referenced_rules <= known_rule_ids

    supported_amounts = set(_currency_values(result))
    claimed_amounts = _response_currency_values(response)
    numeric_claims_supported = claimed_amounts <= supported_amounts if claimed_amounts else True

    if expected_tool == "Guardrail":
        routing_valid = bool(trace and trace[0].startswith("Guardrail:"))
    else:
        routing_valid = any(expected_tool in item for item in trace)

    return {
        "routing_passed": routing_valid,
        "evidence_references_passed": evidence_valid,
        "numeric_claims_passed": numeric_claims_supported,
        "faithfulness_passed": evidence_valid and numeric_claims_supported,
        "passed": routing_valid and evidence_valid and numeric_claims_supported,
        "referenced_transactions": sorted(referenced_transactions),
        "referenced_rules": sorted(referenced_rules),
        "claimed_amounts": sorted(str(value) for value in claimed_amounts),
    }


@contextmanager
def _offline_environment(enabled: bool):
    if not enabled:
        yield
        return
    previous = os.environ.pop("GROQ_API_KEY", None)
    try:
        yield
    finally:
        if previous is not None:
            os.environ["GROQ_API_KEY"] = previous


def run_evaluation_suite(transactions: List[Transaction], profiles: CardProfiles, use_llm: bool = False) -> Dict[str, Any]:
    results = []
    with _offline_environment(enabled=not use_llm):
        for case in CASES:
            response, trace, result = run_agent(case["question"], transactions, profiles)
            evaluation = evaluate_response(response, trace, result, transactions, profiles, case["expected_tool"])
            results.append({"name": case["name"], "question": case["question"], **evaluation})
    return {
        "passed": all(item["passed"] for item in results),
        "routing_accuracy": sum(item["routing_passed"] for item in results),
        "total_cases": len(results),
        "cases": results,
    }


if __name__ == "__main__":
    import json
    from io import BytesIO
    from pathlib import Path

    from validators import load_cards_json, load_transactions_csv

    root = Path(__file__).parent
    transactions = load_transactions_csv(BytesIO((root / "sample_data/transactions.csv").read_bytes()))
    profiles = load_cards_json(BytesIO((root / "sample_data/cards.json").read_bytes()))
    print(json.dumps(run_evaluation_suite(transactions, profiles, use_llm=False), indent=2))

