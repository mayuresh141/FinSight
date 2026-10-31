from decimal import Decimal

from agent import run_agent
from models import CardProfiles, Transaction


def test_fallback_agent_executes_deterministic_tool():
    profiles = CardProfiles.model_validate({
        "cards": [
            {"id": "a", "name": "A", "base_cashback": "0.01", "base_rule_id": "A-BASE"},
            {"id": "b", "name": "B", "base_cashback": "0.04", "base_rule_id": "B-BASE"},
        ]
    })
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="Cafe", amount=Decimal("100"),
        category="dining", card_used="a", transaction_type="purchase"
    )]
    _, trace, analysis = run_agent("Where did I miss cashback?", transactions, profiles)
    assert any("find_missed_rewards" in item for item in trace)
    assert analysis["potential_missed_cashback"] == 3.0 or analysis["potential_missed_cashback"] == "3.00"


def test_missing_requested_card_is_rejected():
    profiles = CardProfiles.model_validate({
        "cards": [{"id": "a", "name": "Card A", "base_cashback": "0.01", "base_rule_id": "A-BASE"}]
    })
    response, trace, analysis = run_agent(
        "How much additional cashback could I have earned using my Chase Sapphire Reserve?",
        [], profiles
    )
    assert "not present" in response
    assert "invent" in response
    assert trace == ["Guardrail: rejected unsupported card comparison"]
    assert analysis == {}


def test_fallback_routes_spending_question_to_spending_tool(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    profiles = CardProfiles.model_validate({
        "cards": [{"id": "a", "name": "A", "base_cashback": "0.01", "base_rule_id": "A-BASE"}]
    })
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="Cafe", amount=Decimal("100"),
        category="dining", card_used="a", transaction_type="purchase"
    )]
    _, trace, result = run_agent("Analyze my spending by category", transactions, profiles)
    assert trace[0] == "analyze_spending: executed deterministic tool"
    assert result["total_purchase_spending"] == "100.00"


def test_fallback_routes_score_question_to_score_tool(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    profiles = CardProfiles.model_validate({
        "cards": [
            {"id": "a", "name": "A", "base_cashback": "0.01", "base_rule_id": "A-BASE"},
            {"id": "b", "name": "B", "base_cashback": "0.04", "base_rule_id": "B-BASE"},
        ]
    })
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="Cafe", amount=Decimal("100"),
        category="dining", card_used="a", transaction_type="purchase"
    )]
    _, trace, result = run_agent("What is my rewards optimization score?", transactions, profiles)
    assert trace[0] == "calculate_score: executed deterministic tool"
    assert result["score"] == "25.00"



