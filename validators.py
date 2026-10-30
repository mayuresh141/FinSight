from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

import pandas as pd

from models import CardProfiles, Transaction


PII_PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    "phone": re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-])\d{3}[\s.-]\d{4}(?!\d)"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "account_or_card_number": re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
}


REQUIRED_TRANSACTION_COLUMNS = {
    "transaction_id", "date", "merchant", "amount", "category", "card_used", "transaction_type"
}


def load_transactions_csv(uploaded_file: Any) -> List[Transaction]:
    frame = pd.read_csv(uploaded_file)
    missing = REQUIRED_TRANSACTION_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError("Missing transaction columns: " + ", ".join(sorted(missing)))

    records = frame.to_dict(orient="records")
    transactions: List[Transaction] = []
    for index, record in enumerate(records, start=2):
        try:
            record["amount"] = Decimal(str(record["amount"]))
            transactions.append(Transaction(**record))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError("Invalid transaction row %d: %s" % (index, exc)) from exc
    return transactions


def load_cards_json(uploaded_file: Any) -> CardProfiles:
    try:
        raw = json.load(uploaded_file)
        return CardProfiles(**raw)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError("Invalid card profile JSON: %s" % exc) from exc


def validate_cross_file_inputs(transactions: List[Transaction], profiles: CardProfiles) -> List[str]:
    card_ids = {card.id for card in profiles.cards}
    errors = []
    for transaction in transactions:
        if transaction.card_used not in card_ids:
            errors.append(
                "Transaction %s references unknown card '%s'."
                % (transaction.transaction_id, transaction.card_used)
            )
    return errors


def validate_in_memory_inputs(transactions: List[Transaction], profiles: CardProfiles) -> None:
    errors = validate_cross_file_inputs(transactions, profiles)
    if errors:
        raise ValueError(" ".join(errors))


def pii_kinds(value: Any) -> List[str]:
    """Return heuristic PII categories found in a value."""
    if not isinstance(value, str):
        return []
    return sorted(kind for kind, pattern in PII_PATTERNS.items() if pattern.search(value))


def redact_pii(value: Any) -> Any:
    """Recursively redact heuristic PII before data is sent to the LLM."""
    if isinstance(value, dict):
        return {key: redact_pii(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [redact_pii(nested) for nested in value]
    if not isinstance(value, str):
        return value
    redacted = value
    for kind, pattern in PII_PATTERNS.items():
        redacted = pattern.sub("[REDACTED_%s]" % kind.upper(), redacted)
    return redacted


def scan_pii_data(transactions: List[Transaction], profiles: CardProfiles) -> List[str]:
    """Scan uploaded transaction/profile values and return detected PII categories."""
    values: List[Any] = []
    for transaction in transactions:
        values.extend(transaction.model_dump().values() if hasattr(transaction, "model_dump") else transaction.dict().values())
    for card in profiles.cards:
        values.extend(card.model_dump().values() if hasattr(card, "model_dump") else card.dict().values())
    found = set()
    for value in values:
        if isinstance(value, dict):
            for nested in value.values():
                found.update(pii_kinds(nested))
        else:
            found.update(pii_kinds(value))
    return sorted(found)

