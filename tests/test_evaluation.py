from decimal import Decimal

from evaluation import evaluate_response, run_evaluation_suite
from models import CardProfiles, Transaction


def data():
    profiles = CardProfiles.model_validate({
        "cards": [
            {"id": "low", "name": "Low Card", "base_cashback": "0.01", "base_rule_id": "LOW-BASE"},
            {"id": "high", "name": "High Card", "base_cashback": "0.04", "base_rule_id": "HIGH-BASE"},
        ]
    })
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="Cafe", amount=Decimal("100"),
        category="dining", card_used="low", transaction_type="purchase"
    )]
    return transactions, profiles


def test_offline_evaluation_suite_passes(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    transactions, profiles = data()
    result = run_evaluation_suite(transactions, profiles, use_llm=False)
    assert result["passed"] is True
    assert result["routing_accuracy"] == 5


def test_faithfulness_rejects_unknown_evidence_reference():
    transactions, profiles = data()
    result = evaluate_response(
        "TX999 earned $100.00 under RULE-FAKE.",
        ["find_missed_rewards: executed deterministic tool"],
        {"potential_missed_cashback": "100.00"},
        transactions,
        profiles,
        "find_missed_rewards",
    )
    assert result["evidence_references_passed"] is False
    assert result["faithfulness_passed"] is False

