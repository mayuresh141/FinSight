from decimal import Decimal

from models import CardProfiles, Transaction
from tools import analyze_spending, calculate_score, find_missed_rewards


def profiles():
    return CardProfiles.model_validate({
        "cards": [
            {"id": "low", "name": "Low Card", "base_cashback": "0.01", "base_rule_id": "LOW-BASE"},
            {"id": "high", "name": "High Card", "base_cashback": "0.04", "base_rule_id": "HIGH-BASE"},
        ]
    })


def test_three_dollar_missed_cashback():
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="Cafe", amount=Decimal("100"),
        category="dining", card_used="low", transaction_type="purchase"
    )]
    result = find_missed_rewards(transactions, profiles())
    assert result.potential_missed_cashback == Decimal("3.00")


def test_unknown_card_fails_without_inventing_rates():
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="Cafe", amount=Decimal("100"),
        category="dining", card_used="missing_card", transaction_type="purchase"
    )]
    try:
        find_missed_rewards(transactions, profiles())
    except ValueError as exc:
        assert "unknown card" in str(exc)
    else:
        raise AssertionError("Expected unknown card validation failure")


def test_analyze_spending_excludes_credit_card_payments():
    transactions = [
        Transaction(transaction_id="TX1", date="2026-10-01", merchant="Cafe", amount=Decimal("100"), category="dining", card_used="low", transaction_type="purchase"),
        Transaction(transaction_id="TX2", date="2026-10-02", merchant="Payment", amount=Decimal("250"), category="transfer", card_used="low", transaction_type="credit_card_payment"),
    ]
    result = analyze_spending(transactions)
    assert result.total_purchase_spending == Decimal("100.00")
    assert result.spending_by_category == {"dining": Decimal("100.00")}


def test_rewards_optimization_score_is_calculated_from_verified_rewards():
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="Cafe", amount=Decimal("100"),
        category="dining", card_used="low", transaction_type="purchase"
    )]
    reward_analysis = find_missed_rewards(transactions, profiles())
    result = calculate_score(reward_analysis)
    assert result.score == Decimal("25.00")
    assert result.status == "calculated"



