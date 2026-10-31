# FinSight Demo Walkthrough Script

Target length: 7-10 minutes

## 1. Opening and problem - 45 seconds

"FinSight is an evidence-grounded AI financial assistant that helps users identify missed credit-card cashback opportunities.

People who use multiple cards often have different reward rules for dining, groceries, travel, gas, and other categories. Choosing the wrong card can reduce the rewards they earn, but reviewing every past transaction manually is time-consuming.

FinSight compares a user's transaction history against their uploaded card profiles and explains where additional cashback may have been possible. The data and card rates in this prototype are synthetic."

## 2. Product choice - 45 seconds

"I considered three problems: missed credit-card rewards, grocery planning and food waste, and rental move-in damage documentation.

I selected FinSight because its value is measurable in dollars, its calculations can be verified deterministically, and it can be built end-to-end within the four-hour constraint without banking integrations or paid services.

The prototype tests technical feasibility, not consumer demand. User demand would require interviews and behavior testing."

## 3. Architecture and agent - 1 minute

"The central design decision is to separate orchestration from financial correctness.

The Groq-powered agent interprets the user's natural-language question and selects one or more tools. The tools are deterministic Python functions. They validate inputs, perform currency calculations, compare reward rules, and return structured results.

The LLM never calculates cashback itself. It only explains verified tool output. This gives us conversational flexibility while keeping the financial logic auditable. The agent supports bounded multi-step tool calling, so it can call one tool or build a short dependency chain when a question requires it."

## 4. Tool demonstration - 3 minutes

### Spending analysis

Select `Synthetic 60 transactions` and ask:

> Analyze my spending by category for October and identify my top three categories.

"The agent selects `analyze_spending`. This tool excludes refunds, transfers, and credit-card payments, then calculates eligible spending by category."

### Missed cashback

Ask:

> Where did I miss cashback? Show the five highest-value opportunities with transaction IDs and reward-rule IDs.

"The agent selects `find_missed_rewards`. For each eligible purchase, Python calculates the reward from the card actually used, compares it with the best uploaded alternative, and returns the potential difference.

Each finding includes a transaction ID, merchant, card used, recommended card, actual reward, alternative reward, additional cashback, and supporting rule ID."

### Rewards score

Ask:

> What is my Rewards Optimization Score? Explain the formula using my verified cashback results.

"The agent may first call `find_missed_rewards`, then call `calculate_score`. The score is calculated as actual eligible rewards divided by maximum achievable eligible rewards, multiplied by 100.

If the denominator is zero or required inputs are missing, the tool returns an unavailable status instead of inventing a score."

## 5. Guardrails - 1 minute

### Unsupported card

Ask:

> How much additional cashback could I have earned using my Chase Sapphire Reserve?

"That card is not in the uploaded profiles. FinSight refuses the comparison and asks the user to add its synthetic reward rules. It does not use external card knowledge or invent a rate."

"The upload path detects likely emails, phone numbers, SSNs, and long account or card numbers. Matching values are redacted before tool results are sent to Groq. This is heuristic demo protection, not a compliance system."

## 6. Evaluation - 30 seconds

Run in the terminal:

```bash
.venv/bin/python -m evaluation
```

"The offline evaluation suite checks the missed-rewards and score workflows.

It measures relevance through expected tool routing and faithfulness by checking that transaction IDs, reward-rule IDs, and currency claims are supported by deterministic tool results."

## 7. Design decisions and limitations - 1 minute

"I chose native Groq tool calling instead of LangChain to keep the prototype small and make the orchestration easy to inspect. The system uses synthetic data rather than banking integrations because external account access was unnecessary for the core workflow.

Implemented features include the Streamlit interface, three deterministic tools, native tool calling, validation, evidence traces, PII warnings and redaction, and focused evaluation tests.

Deferred features include quarterly reward caps, rotating categories, activation requirements, merchant-specific offers, external benefit verification, authentication, databases, and production deployment.

Codex was used as an AI engineering assistant for implementation support, debugging, tests, documentation, and PDF preparation. The problem selection, architecture, scope, guardrails, trade-offs, and final design decisions were mine, and I verified the implementation through tests, evaluation runs, live Groq checks, sample-data validation, and visual inspection."

## 8. Closing - 20 seconds

"The main design principle is that the LLM decides which analysis to run, but Python remains the source of truth for financial calculations. That makes FinSight conversational, explainable, and appropriately bounded for a four-hour prototype."

