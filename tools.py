from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from models import (
    CardProfile,
    CardProfiles,
    MissedRewardFinding,
    RewardAnalysis,
    ScoreResult,
    SpendingAnalysis,
    Transaction,
)
from validators import validate_in_memory_inputs


CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def eligible_transactions(transactions: List[Transaction]) -> List[Transaction]:
    excluded = {"transfer", "refund", "credit_card_payment"}
    return [
        tx for tx in transactions
        if tx.transaction_type.lower() not in excluded and tx.amount > 0
    ]


def analyze_spending(transactions: List[Transaction]) -> SpendingAnalysis:
    """Summarize eligible purchase spending using only validated transactions."""
    eligible = eligible_transactions(transactions)
    by_category: Dict[str, Decimal] = {}
    for transaction in eligible:
        by_category[transaction.category] = by_category.get(transaction.category, Decimal("0")) + transaction.amount
    by_category = {category: money(amount) for category, amount in by_category.items()}
    ordered_categories = sorted(by_category, key=lambda category: by_category[category], reverse=True)
    return SpendingAnalysis(
        total_purchase_spending=money(sum(by_category.values(), Decimal("0"))),
        spending_by_category=by_category,
        largest_categories=ordered_categories[:3],
        transaction_ids=[transaction.transaction_id for transaction in eligible],
    )


def reward_for(card: CardProfile, category: str, amount: Decimal):
    rule = card.categories.get(category)
    if rule:
        return money(amount * rule.rate), rule.rule_id
    return money(amount * card.base_cashback), card.base_rule_id


def find_missed_rewards(transactions: List[Transaction], profiles: CardProfiles) -> RewardAnalysis:
    """Compare each eligible purchase against only the user-supplied card rules."""
    validate_in_memory_inputs(transactions, profiles)
    cards = {card.id: card for card in profiles.cards}
    findings: List[MissedRewardFinding] = []
    actual_total = Decimal("0")
    maximum_total = Decimal("0")

    for transaction in eligible_transactions(transactions):
        used_card = cards[transaction.card_used]
        actual_reward, _ = reward_for(used_card, transaction.category, transaction.amount)
        candidates = []
        for card in profiles.cards:
            reward, rule_id = reward_for(card, transaction.category, transaction.amount)
            candidates.append((reward, card, rule_id))
        best_reward, best_card, best_rule_id = max(candidates, key=lambda item: item[0])
        actual_total += actual_reward
        maximum_total += best_reward
        additional = money(best_reward - actual_reward)
        if additional > 0 and best_card.id != used_card.id:
            findings.append(MissedRewardFinding(
                transaction_id=transaction.transaction_id,
                merchant=transaction.merchant,
                amount=money(transaction.amount),
                category=transaction.category,
                card_actually_used=used_card.name,
                recommended_alternative_card=best_card.name,
                actual_reward_amount=actual_reward,
                alternative_reward_amount=best_reward,
                potential_additional_cashback=additional,
                supporting_reward_rule_id=best_rule_id,
            ))

    actual_total = money(actual_total)
    maximum_total = money(maximum_total)
    return RewardAnalysis(
        eligible_transaction_count=len(eligible_transactions(transactions)),
        actual_estimated_cashback=actual_total,
        maximum_estimated_cashback=maximum_total,
        potential_missed_cashback=money(maximum_total - actual_total),
        findings=findings,
        assumptions=[
            "Card rates and reward rules come only from the uploaded synthetic profiles.",
            "Positive purchase amounts are treated as spending.",
            "Transfers, refunds, and credit-card payments are excluded.",
            "Currency values are rounded to cents using ROUND_HALF_UP.",
        ],
    )


def calculate_score(reward_analysis: RewardAnalysis) -> ScoreResult:
    """Calculate rewards optimization, never treating missing data as zero."""
    maximum = reward_analysis.maximum_estimated_cashback
    if maximum <= 0:
        return ScoreResult(
            actual_estimated_cashback=reward_analysis.actual_estimated_cashback,
            maximum_estimated_cashback=maximum,
            potential_missed_cashback=reward_analysis.potential_missed_cashback,
            score=None,
            status="unavailable",
            explanation="The score is unavailable because maximum achievable eligible rewards are zero or missing.",
        )
    score = money((Decimal("100") * reward_analysis.actual_estimated_cashback / maximum).min(Decimal("100")))
    return ScoreResult(
        actual_estimated_cashback=reward_analysis.actual_estimated_cashback,
        maximum_estimated_cashback=maximum,
        potential_missed_cashback=reward_analysis.potential_missed_cashback,
        score=score,
        status="calculated",
        explanation="Score = 100 x (actual eligible rewards / maximum achievable eligible rewards).",
    )


def generate_report(transactions: List[Transaction], profiles: CardProfiles) -> str:
    """Generate Markdown exclusively from verified deterministic tool results."""
    spending = analyze_spending(transactions)
    rewards = find_missed_rewards(transactions, profiles)
    score = calculate_score(rewards)
    lines = [
        "# FinSight Financial Rewards Report",
        "",
        "> Prototype analysis using synthetic card profiles. This is not financial advice.",
        "",
        "## Spending summary",
        "",
        "- Eligible purchase spending: **$%s**" % spending.total_purchase_spending,
        "- Eligible transactions: **%d**" % len(spending.transaction_ids),
        "",
        "### Spending by category",
        "",
    ]
    for category, amount in spending.spending_by_category.items():
        lines.append("- `%s`: $%s" % (category, amount))
    lines.extend([
        "",
        "## Missed cashback opportunities",
        "",
        "- Actual estimated cashback: **$%s**" % rewards.actual_estimated_cashback,
        "- Maximum estimated cashback: **$%s**" % rewards.maximum_estimated_cashback,
        "- Potential missed cashback: **$%s**" % rewards.potential_missed_cashback,
        "",
    ])
    if rewards.findings:
        lines.extend([
            "| Transaction | Merchant | Used card | Recommended card | Additional cashback | Rule |",
            "|---|---|---|---|---:|---|",
        ])
        for finding in rewards.findings:
            lines.append(
                "| %s | %s | %s | %s | $%s | %s |" % (
                    finding.transaction_id, finding.merchant, finding.card_actually_used,
                    finding.recommended_alternative_card, finding.potential_additional_cashback,
                    finding.supporting_reward_rule_id,
                )
            )
    else:
        lines.append("No missed cashback opportunities were found.")
    lines.extend([
        "",
        "## Rewards Optimization Score",
        "",
        "- Score: **%s**" % ("Unavailable" if score.score is None else "%s/100" % score.score),
        "- Actual eligible rewards: **$%s**" % score.actual_estimated_cashback,
        "- Maximum achievable eligible rewards: **$%s**" % score.maximum_estimated_cashback,
        "- Formula: %s" % score.explanation,
        "",
        "## Assumptions and limitations",
        "",
    ])
    for assumption in rewards.assumptions:
        lines.append("- " + assumption)
    lines.extend([
        "- Quarterly caps, rotating categories, activation requirements, merchant offers, and external benefit verification are deferred.",
        "- Card profiles and reward rates are synthetic and supplied by the user.",
    ])
    return "\n".join(lines) + "\n"


def analysis_as_dict(analysis: RewardAnalysis) -> Dict[str, Any]:
    if hasattr(analysis, "model_dump"):
        return analysis.model_dump(mode="json")
    return analysis.dict()

