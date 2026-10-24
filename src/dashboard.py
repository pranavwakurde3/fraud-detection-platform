import sqlite3
import pandas as pd
import streamlit as st

DB = "data/scores.db"
st.set_page_config(page_title="Fraud Analyst Dashboard", layout="wide")
st.title("Fraud Analyst Dashboard")


def q(sql, params=()):
    con = sqlite3.connect(DB, timeout=10)
    try:
        return pd.read_sql(sql, con, params=params)
    finally:
        con.close()


def run(sql, params=()):
    con = sqlite3.connect(DB, timeout=10)
    try:
        con.execute(sql, params)
        con.commit()
    finally:
        con.close()


try:
    s = q("SELECT * FROM scores")
except Exception as e:
    st.error(f"Cannot read {DB}. Run the producer and consumer first. ({e})")
    st.stop()

threshold = st.sidebar.slider("Alert threshold", 0.05, 0.95, 0.50, 0.05)
st.sidebar.caption("Transactions with a score at or above this value are alerts.")

alerts = s[s.fraud_score >= threshold]
reviewed = alerts[alerts.status != "new"]
confirmed = (reviewed.status == "confirmed_fraud").sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Transactions scored", len(s))
c2.metric("Alerts", len(alerts))
c3.metric("Open cases", int((alerts.status == "new").sum()))
c4.metric("Avg latency (ms)", round(s.latency_ms.mean(), 1) if len(s) else 0)
c5.metric("Analyst precision", f"{confirmed / len(reviewed):.0%}" if len(reviewed) else "n/a")

st.subheader("Cases to review (highest risk first)")
view = st.radio("Show", ["Open", "All alerts"], horizontal=True)
cases = alerts if view == "All alerts" else alerts[alerts.status == "new"]
cases = cases.sort_values("fraud_score", ascending=False)
st.dataframe(
    cases[["transaction_id", "card_id", "fraud_score", "status", "latency_ms", "true_label"]]
    .rename(columns={"true_label": "true_label (demo only)"}),
    use_container_width=True, height=300)

st.subheader("Review a case")
if len(cases):
    tid = st.selectbox("Transaction ID", cases.transaction_id.tolist())
    row = s[s.transaction_id == tid].iloc[0]
    st.write(f"Score **{row.fraud_score:.3f}** | card **{int(row.card_id)}** | "
             f"current status **{row.status}**")
    b1, b2, b3 = st.columns(3)
    for col, label, status, lab in [
        (b1, "Confirm fraud", "confirmed_fraud", 1),
        (b2, "False alarm", "false_alarm", 0),
        (b3, "Escalate", "escalated", None),
    ]:
        if col.button(label, key=f"{label}_{tid}"):
            run("UPDATE scores SET status=?, analyst_label=? WHERE transaction_id=?",
                (status, lab, int(tid)))
            st.rerun()
else:
    st.info("No cases to show. Lower the threshold or send more transactions.")

st.subheader("Feedback labels")
fb = q("SELECT transaction_id, card_id, fraud_score, status, analyst_label "
       "FROM scores WHERE analyst_label IS NOT NULL")
st.write(f"{len(fb)} labelled by analysts")
st.download_button("Download feedback labels (CSV)", fb.to_csv(index=False), "feedback_labels.csv")
