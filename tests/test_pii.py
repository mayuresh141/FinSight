from decimal import Decimal

from agent import run_agent
from models import CardProfiles, Transaction
from validators import redact_pii, scan_pii_data


def test_pii_is_detected_and_redacted():
    profiles = CardProfiles.model_validate({
        "cards": [{"id": "a", "name": "Card A", "base_cashback": "0.01", "base_rule_id": "A-BASE"}]
    })
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="Jane Doe jane@example.com 555-123-4567",
        amount=Decimal("100"), category="dining", card_used="a", transaction_type="purchase"
    )]
    detected = scan_pii_data(transactions, profiles)
    assert "email" in detected
    assert "phone" in detected
    redacted = redact_pii({"merchant": transactions[0].merchant})
    assert "jane@example.com" not in redacted["merchant"]
    assert "555-123-4567" not in redacted["merchant"]


def test_agent_result_does_not_expose_detected_pii(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    profiles = CardProfiles.model_validate({
        "cards": [{"id": "a", "name": "Card A", "base_cashback": "0.01", "base_rule_id": "A-BASE"}]
    })
    transactions = [Transaction(
        transaction_id="TX1", date="2026-10-01", merchant="jane@example.com", amount=Decimal("100"),
        category="dining", card_used="a", transaction_type="purchase"
    )]
    response, _, result = run_agent("Where did I miss cashback?", transactions, profiles)
    assert "jane@example.com" not in response
    assert "jane@example.com" not in str(result)


def test_agent_explicitly_refuses_direct_ssn_request(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    profiles = CardProfiles.model_validate({
        "cards": [{"id": "a", "name": "Card A", "base_cashback": "0.01", "base_rule_id": "A-BASE"}]
    })
    response, trace, result = run_agent("What is the SSN in the uploaded file?", [], profiles)
    assert "cannot reveal" in response
    assert trace == ["Guardrail: refused direct PII retrieval request"]
    assert result == {}

