from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import analyze_spending, find_missed_rewards  # noqa: E402
from validators import load_cards_json, load_transactions_csv  # noqa: E402


OUT = ROOT / "output" / "pdf" / "finsight_case_study_submission.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#14213D")
BLUE = colors.HexColor("#2563EB")
TEAL = colors.HexColor("#0F766E")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#5B6475")
PALE_BLUE = colors.HexColor("#EFF6FF")
PALE_TEAL = colors.HexColor("#ECFDF5")
LINE = colors.HexColor("#D8DEE9")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverKicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=BLUE, spaceAfter=8))
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27, leading=31, textColor=NAVY, alignment=TA_LEFT, spaceAfter=7))
styles.add(ParagraphStyle(name="CoverSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=14, leading=18, textColor=MUTED, spaceAfter=18))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NAVY, spaceBefore=4, spaceAfter=9))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=TEAL, spaceBefore=9, spaceAfter=4))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.1, leading=12.2, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=10.2, textColor=MUTED, spaceAfter=3))
styles.add(ParagraphStyle(name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.2, leading=10, textColor=colors.white))
styles.add(ParagraphStyle(name="TableCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.8, leading=9.5, textColor=INK))
styles.add(ParagraphStyle(name="TableCellBold", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.8, leading=9.5, textColor=NAVY))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=NAVY, spaceAfter=0))


def P(text, style="Bodyx"):
    return Paragraph(text, styles[style])


def bullets(items):
    return [P("- " + item, "Bodyx") for item in items]


def section_title(text):
    return P(text, "H2x")


def callout(title, body, background=PALE_BLUE):
    table = Table([[P(title, "Callout"), P(body, "Bodyx")]], colWidths=[1.48 * inch, 5.72 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#BFDBFE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(0.65 * inch, 0.48 * inch, width - 0.65 * inch, 0.48 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.65 * inch, 0.29 * inch, "FinSight | Candidate case study")
    canvas.drawRightString(width - 0.65 * inch, 0.29 * inch, "Page %d" % doc.page)
    canvas.restoreState()


def make_doc():
    doc = BaseDocTemplate(
        str(OUT), pagesize=letter, leftMargin=0.68 * inch, rightMargin=0.68 * inch,
        topMargin=0.62 * inch, bottomMargin=0.68 * inch, title="FinSight Case Study Submission",
        author="FinSight candidate",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=frame, onPage=footer)])
    return doc


def build_story():
    transactions = load_transactions_csv(BytesIO((ROOT / "sample_data" / "transactions.csv").read_bytes()))
    profiles = load_cards_json((ROOT / "sample_data" / "cards.json").open("rb"))
    spending = analyze_spending(transactions)
    rewards = find_missed_rewards(transactions, profiles)

    story = []

    # Page 1: problem selection
    story += [P("CASE STUDY 1 | CANDIDATE BRIEF", "CoverKicker"), P("FinSight", "CoverTitle"), P("Evidence-Grounded AI Financial Assistant", "CoverSubtitle")]
    story.append(callout("Decision summary", "Build a focused assistant that compares real transaction behavior against user-supplied synthetic card rules, identifies missed cashback, and explains every recommendation with transaction and rule evidence."))
    story += [Spacer(1, 12), P("1. Choose a problem worth solving", "H1x")]
    story.append(P("I considered three everyday problems where software and AI could help users make better decisions.", "Bodyx"))
    problem_data = [
        [P("Candidate problem", "TableHead"), P("Where / who", "TableHead"), P("Consequence", "TableHead")],
        [P("Missed credit card rewards<br/><font color='#5B6475'>FinSight</font>", "TableCellBold"), P("Encountered while comparing card benefits across past purchases. Consumers using multiple cards, especially across dining, groceries, and travel.", "TableCell"), P("Users may consistently miss cashback without realizing how much they could have earned.", "TableCell")],
        [P("Grocery planning and food waste<br/><font color='#5B6475'>PantryPilot</font>", "TableCellBold"), P("Encountered when shopping lists are made without checking existing ingredients. Students, professionals, and households on a budget.", "TableCell"), P("Duplicate purchases, higher grocery expenses, unused ingredients, and avoidable food waste.", "TableCell")],
        [P("Rental move-in damage documentation<br/><font color='#5B6475'>RentGuard</font>", "TableCellBold"), P("Encountered during manual move-in inspections. Renters, especially students and frequent movers.", "TableCell"), P("Incomplete documentation can create disputes and unexpected security-deposit deductions.", "TableCell")],
    ]
    table = Table(problem_data, colWidths=[1.85 * inch, 2.05 * inch, 3.3 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story += [table, section_title("Why I selected FinSight"), P("FinSight addresses a recurring financial decision with a measurable outcome: additional cashback that a user could potentially have earned. I selected it for three reasons: measurable value, appropriate use of AI, and feasibility within the four-hour constraint. The LLM interprets questions, selects tools, and explains findings; deterministic Python functions handle financial calculations.", "Bodyx"), P("PantryPilot was promising, but useful recommendations would require pantry inventory, dietary preferences, and ingredient availability. RentGuard offered interesting computer-vision opportunities, but reliable damage assessment would require image processing and more extensive validation. FinSight offered the clearest path to a small, testable prototype demonstrating AI orchestration and trustworthy calculations.", "Bodyx")]
    story += [section_title("Observations versus assumptions"), P("Observed: credit cards can offer different reward rates across categories; comparing multiple cards and transactions requires several calculations; given transaction amounts and defined cashback rules, reward differences can be calculated deterministically.", "Bodyx"), P("Assumptions to validate: users find rewards optimization difficult enough to use an assistant; users are comfortable uploading transaction data and card profiles; retrospective analysis improves future card selection; and natural-language interaction adds value beyond a comparison dashboard. The prototype tests technical feasibility, not consumer demand.", "Bodyx")]
    story.append(PageBreak())

    # Page 2: approach
    story += [P("2. Develop the approach", "H1x"), section_title("How the problem is handled today"), P("A user can inspect each transaction, remember each card's category benefits, compare alternatives, and calculate the difference manually. A spreadsheet can help, but the user still has to encode the rules and decide which analysis to run.", "Bodyx"), section_title("Better outcome"), P("A user uploads transactions and card rules, asks a plain-language question, and receives a concise answer backed by transaction IDs, reward-rule IDs, and transparent calculations. Unsupported cards should fail explicitly rather than producing plausible-looking estimates.", "Bodyx")]
    story.append(callout("Smallest useful first step", "A deterministic missed-rewards comparison for eligible purchases, wrapped by one real LLM tool-calling path. This is the core workflow; spending analysis and scoring extend it only after the calculation is reliable.", PALE_TEAL))
    story += [section_title("Architecture and responsibility split"), P("The LLM is an orchestrator, not a calculator. It selects a tool, receives verified structured output, and explains the result. Python owns validation, currency arithmetic, eligibility rules, reward comparisons, score calculation, and PII redaction.", "Bodyx")]
    arch = Table([[P("User question", "TableHead"), P("Groq agent", "TableHead"), P("Deterministic tools", "TableHead"), P("Grounded response", "TableHead")], [P("Natural-language intent", "TableCell"), P("Selects one or more tools", "TableCell"), P("Compute and validate results", "TableCell"), P("Explain with evidence", "TableCell")]], colWidths=[1.7 * inch, 1.7 * inch, 2.0 * inch, 1.8 * inch])
    arch.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("BACKGROUND", (0, 1), (-1, 1), PALE_BLUE), ("GRID", (0, 0), (-1, -1), 0.45, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story += [arch, section_title("Alternative considered"), P("A rules-only spreadsheet would be simpler and highly transparent, but it would not demonstrate natural-language intent handling or agent orchestration. An agent-first design that let the LLM calculate rewards would be more flexible but would weaken correctness. FinSight combines the two: deterministic financial tools behind a bounded, native Groq tool-calling loop.", "Bodyx"), section_title("What must be learned and when to stop"), P("Next: test whether users understand the evidence, whether the recommended alternative card changes behavior, and whether the time saved is meaningful. The problem is not worth expanding if users do not trust the synthetic rules, cannot act on the recommendations, or see too little missed value to justify maintaining card profiles.", "Bodyx")]
    story.append(PageBreak())

    # Page 3: prototype and evidence
    story += [P("3. Build a working prototype", "H1x"), P("FinSight is a Streamlit application using Python, Pandas, Pydantic, the Groq SDK, and deterministic functions. It accepts a transactions CSV and card-profiles JSON. The sample dataset contains %d transactions, of which %d are eligible purchases. In the current synthetic sample, the tool identifies $%s in potential missed cashback." % (len(transactions), len(spending.transaction_ids), rewards.potential_missed_cashback), "Bodyx")]
    tools_data = [
        [P("Tool", "TableHead"), P("Purpose", "TableHead"), P("Evidence / safety", "TableHead")],
        [P("analyze_spending", "TableCellBold"), P("Summarize eligible spending and categories.", "TableCell"), P("Excludes transfers, refunds, and credit-card payments.", "TableCell")],
        [P("find_missed_rewards", "TableCellBold"), P("Compare actual and best available reward for each purchase.", "TableCell"), P("Returns transaction ID, card names, amounts, and rule ID; all math is Python Decimal.", "TableCell")],
        [P("calculate_score", "TableCellBold"), P("Compute Rewards Optimization Score.", "TableCell"), P("Score is unavailable rather than fabricated when the denominator is zero or missing.", "TableCell")],
    ]
    tools_table = Table(tools_data, colWidths=[1.55 * inch, 2.55 * inch, 3.1 * inch], repeatRows=1)
    tools_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.45, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])]))
    story += [section_title("Tool contract"), tools_table, section_title("Representative use case"), P("Prompt: 'Where did I miss cashback?' The agent selects find_missed_rewards. The tool compares each eligible purchase against the uploaded profiles, returns only supported alternatives, and the assistant explains the highest-value opportunities with evidence references.", "Bodyx"), section_title("Difficult or invalid-input case"), P("Prompt: 'How much additional cashback could I have earned using my Chase Sapphire Reserve?' The card is absent from the uploaded profiles. A deterministic guardrail rejects the comparison and asks the user to add a synthetic profile. The system does not use external card knowledge or invent a rate.", "Bodyx"), section_title("PII guardrail"), P("The upload path heuristically detects emails, phone numbers, SSNs, and long account/card numbers. Detected values are redacted before tool results are sent to Groq. This is explicitly demo protection, not a compliance-grade system; synthetic data remains the intended submission mode.", "Bodyx")]
    story.append(PageBreak())

    # Page 4: evaluation, constraints, submission
    story += [P("4. Evaluation, constraints, and submission", "H1x"), section_title("Evaluation approach"), P("The offline evaluation suite runs two core scenarios: missed rewards and score. It checks routing relevance, valid transaction and reward-rule references, and numeric claims against deterministic tool results. The current suite passes 2/2 cases, with 8 focused automated tests passing overall.", "Bodyx")]
    eval_table = Table([[P("Dimension", "TableHead"), P("Check", "TableHead"), P("Current result", "TableHead")], [P("Relevance", "TableCellBold"), P("Expected intent reaches the expected tool.", "TableCell"), P("2/2 core cases pass", "TableCell")], [P("Faithfulness", "TableCellBold"), P("References and currency claims are supported by tool outputs.", "TableCell"), P("Pass", "TableCell")], [P("Safety", "TableCellBold"), P("Unsupported card is rejected; PII is redacted heuristically.", "TableCell"), P("Pass", "TableCell")]], colWidths=[1.45 * inch, 3.55 * inch, 2.2 * inch], repeatRows=1)
    eval_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.45, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [eval_table, section_title("Time and implementation disclosure"), P("Time spent: approximately four hours. No prior work was reused. Codex was used as an AI engineering assistant for implementation support, debugging, test creation, documentation, and PDF preparation. I made the problem selection, product direction, architecture, tool boundaries, guardrails, scope, trade-offs, and final design decisions. Codex output was checked through unit tests, sample-data validation, live Groq smoke tests, evaluation checks, and visual inspection. The submission does not require a paid service or production account.", "Bodyx"), section_title("Implemented, mocked, and deferred")]
    story += bullets(["Implemented: Streamlit UI, native Groq tool calling, three deterministic tools, validation, PII warning/redaction, evidence traces, sample data, and focused evaluation tests.", "Mocked/synthetic: transaction history, card profiles, reward rates, and all card benefits. No claim is made that the rates represent real products.", "Deferred: quarterly caps, rotating categories, activation requirements, merchant-specific offers, external benefit verification, authentication, and databases."])
    story += [section_title("Submission plan"), P("The video walkthrough will demonstrate the core cashback question, the score workflow, the unsupported-card failure case, the PII guardrail concept, and the evaluation suite. The prototype is intentionally narrow: the strongest claim is that the core workflow is real, explainable, and safe against the failure modes selected for this exercise.", "Bodyx"), Spacer(1, 8), callout("Final takeaway", "FinSight treats the LLM as a bounded decision-maker and Python as the source of financial truth. That design keeps the demo useful, auditable, and achievable within the time limit.", PALE_TEAL)]
    return story


if __name__ == "__main__":
    make_doc().build(build_story())
    print(OUT)

