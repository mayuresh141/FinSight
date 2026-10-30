from __future__ import annotations

import io
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agent import run_agent
from validators import load_cards_json, load_transactions_csv, scan_pii_data, validate_cross_file_inputs


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


st.set_page_config(page_title="FinSight", page_icon="💳", layout="wide")
st.title("FinSight")
st.caption("Evidence-grounded missed-cashback analysis using your uploaded synthetic card rules.")
st.info("Prototype only: rates are user-provided synthetic rules and this is not financial advice.")


@st.cache_data
def sample_bytes(path: str) -> bytes:
    return (ROOT / path).read_bytes()


with st.sidebar:
    st.header("Inputs")
    dataset_mode = st.selectbox(
        "Choose a dataset",
        ["Synthetic 60 transactions", "PII guardrail test data", "Upload my own files"],
    )

    if dataset_mode == "Upload my own files":
        transaction_file = st.file_uploader("Transactions CSV", type=["csv"])
        cards_file = st.file_uploader("Card profiles JSON", type=["json"])
    else:
        dataset_path = "sample_data/transactions.csv" if dataset_mode == "Synthetic 60 transactions" else "sample_data/transactions_pii_test.csv"
        transaction_file = io.BytesIO(sample_bytes(dataset_path))
        transaction_file.name = dataset_path.rsplit("/", 1)[-1]
        cards_file = io.BytesIO(sample_bytes("sample_data/cards.json"))
        cards_file.name = "cards.json"

if not transaction_file or not cards_file:
    st.warning("Choose a built-in dataset or upload both files.")
    st.stop()

try:
    transactions = load_transactions_csv(transaction_file)
    cards = load_cards_json(cards_file)
    validation_errors = validate_cross_file_inputs(transactions, cards)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if validation_errors:
    st.error("Input validation failed: " + " ".join(validation_errors))
    st.stop()

detected_pii = scan_pii_data(transactions, cards)
if detected_pii:
    st.warning(
        "Possible PII detected (%s). Values matching these patterns will be redacted before tool results are sent to Groq. "
        "This is heuristic protection; use synthetic data for the demo." % ", ".join(detected_pii)
    )

st.success("Validated %d transactions and %d card profiles." % (len(transactions), len(cards.cards)))
question = st.chat_input("Ask: Where did I miss cashback?")

if "messages" not in st.session_state:
    st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        response, trace, analysis = run_agent(question, transactions, cards)
        st.markdown(response)
        with st.expander("Evidence and tool trace"):
            st.json(analysis)
            for item in trace:
                st.write("- " + item)
            if analysis.get("report"):
                st.download_button(
                    "Download Markdown report",
                    data=analysis["report"],
                    file_name="finsight_report.md",
                    mime="text/markdown",
                )
    st.session_state.messages.append({"role": "assistant", "content": response})

