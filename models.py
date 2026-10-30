from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RewardRule(BaseModel):
    rate: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    rule_id: str


class CardProfile(BaseModel):
    id: str
    name: str
    base_cashback: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    base_rule_id: str
    categories: Dict[str, RewardRule] = Field(default_factory=dict)


class CardProfiles(BaseModel):
    cards: List[CardProfile]


class Transaction(BaseModel):
    transaction_id: str
    date: str
    merchant: str
    amount: Decimal
    category: str
    card_used: str
    transaction_type: str


class MissedRewardFinding(BaseModel):
    transaction_id: str
    merchant: str
    amount: Decimal
    category: str
    card_actually_used: str
    recommended_alternative_card: str
    actual_reward_amount: Decimal
    alternative_reward_amount: Decimal
    potential_additional_cashback: Decimal
    supporting_reward_rule_id: str


class RewardAnalysis(BaseModel):
    eligible_transaction_count: int
    actual_estimated_cashback: Decimal
    maximum_estimated_cashback: Decimal
    potential_missed_cashback: Decimal
    findings: List[MissedRewardFinding]
    assumptions: List[str]


class SpendingAnalysis(BaseModel):
    total_purchase_spending: Decimal
    spending_by_category: Dict[str, Decimal]
    largest_categories: List[str]
    transaction_ids: List[str]


class ScoreResult(BaseModel):
    actual_estimated_cashback: Decimal
    maximum_estimated_cashback: Decimal
    potential_missed_cashback: Decimal
    score: Optional[Decimal]
    explanation: str
    status: str

