import pandas as pd, requests, json

cols = json.load(open("models/serving_features.json"))["message"]
f = pd.read_parquet("data/features.parquet", columns=["TransactionID", "card_id", "event_timestamp", "isFraud"])
raw = pd.read_csv("data/train_transaction.csv", usecols=["TransactionID"] + cols)
df = f.merge(raw, on="TransactionID").sort_values("event_timestamp")
test = df.iloc[int(len(df) * 0.8):]
sample = pd.concat([test[test.isFraud == 1].head(5), test[test.isFraud == 0].head(5)])

for _, r in sample.iterrows():
    msg = {"transaction_id": int(r.TransactionID), "card_id": int(r.card_id)}
    for c in cols:
        msg[c] = None if pd.isna(r[c]) else float(r[c])
    out = requests.post("http://127.0.0.1:8000/score", json=msg).json()
    print("true:", int(r.isFraud), "| score:", out["fraud_score"], "| alert:", out["alert"], "|", out["latency_ms"], "ms")
