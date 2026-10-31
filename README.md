# FinSight

FinSight is a focused prototype for detecting missed credit-card cashback opportunities using only user-supplied transaction data and synthetic card reward rules.

Live demo: https://finsight-nes2ccxnythb832nzsiinh.streamlit.app/

## Core workflow

1. Load a transactions CSV and card-profiles JSON.
2. Validate schemas and cross-file card references.
3. Let the Groq agent choose among three tools: spending analysis, missed-rewards analysis, and rewards-score calculation.
4. Return transaction-level evidence, reward-rule IDs, spending summaries, or score components.
5. Use deterministic Python results as the only source for the LLM explanation.

This prototype is not financial advice. Card rates in the sample data are synthetic and do not represent real products.

The app includes heuristic PII detection for emails, phone numbers, SSNs, and long account/card numbers. Matching values are redacted from tool results before they are sent to Groq. This is a demo guardrail, not comprehensive privacy or compliance protection; use synthetic data for evaluation.

## AI assistance and authorship

Codex was used as an AI engineering assistant for implementation support, debugging, test creation, documentation, and PDF preparation. I made the problem selection, FinSight product direction, architecture, tool boundaries, guardrails, scope, trade-offs, and final design decisions. Codex output was checked through unit tests, evaluation runs, live Groq smoke tests, sample-data validation, and visual inspection.

## Setup

Python 3.9+ is supported for this prototype. The implementation was verified locally with Python 3.9.6.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `GROQ_API_KEY` in your shell or `.env`. Do not commit the key. The app still runs its deterministic analysis if the key or `groq` package is unavailable, but the real LLM tool-calling path will be skipped and clearly marked.

## Run

```bash
streamlit run app.py
```

The same Streamlit application is deployed at the live demo URL above.

Use the synthetic example data first. The app accepts positive purchase amounts and excludes transfers, refunds, and credit-card payments. Currency is calculated with `Decimal` and displayed to cents using `ROUND_HALF_UP`.

## Test

```bash
pytest -q
```

Tests cover the $100 / 1% versus 4% calculation, unknown-card rejection, deterministic tool execution, routing, and faithfulness checks. Groq routing is only considered demonstrated when the UI trace shows that the LLM selected the relevant tool.

## Evaluation

Run the offline evaluation suite without making API calls:

```bash
python -m evaluation
```

The suite checks the core cashback and score workflows: routing relevance, valid transaction and reward-rule references, and numeric claims against deterministic tool results. Set `use_llm=True` in Python only when you intentionally want to evaluate live Groq routing.

## Implemented, mocked, and deferred

Implemented: deterministic spending analysis, cashback comparison, rewards optimization score, Pydantic validation, Streamlit upload/chat UI, bounded multi-step Groq tool calling, evidence trace, PII detection/redaction, synthetic data, and focused tests.

Mocked/synthetic: card profiles, reward rates, and transaction history.

Deferred future work: additional tools for monthly spending trends, recurring-spend detection, card-profile management, and richer comparisons; stronger guardrails for ambiguous categories, rule freshness and provenance, user confirmation, and comprehensive PII handling; and production capabilities such as authentication, secure storage, external benefit verification, and broader evaluation.

