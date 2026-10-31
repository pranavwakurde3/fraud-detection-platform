import json, time, sys
import pandas as pd
from kafka import KafkaProducer

RATE = float(sys.argv[1]) if len(sys.argv) > 1 else 5   # messages per second
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 200  # how many to send

f = pd.read_parquet("data/features.parquet", columns=["TransactionID", "card_id", "event_timestamp", "isFraud"])
raw = pd.read_csv("data/train_transaction.csv", usecols=["TransactionID", "TransactionAmt"])
df = f.merge(raw, on="TransactionID").sort_values("event_timestamp")
df = df.iloc[int(len(df) * 0.8):].head(LIMIT)

producer = KafkaProducer(bootstrap_servers="localhost:9092",
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"))

for _, r in df.iterrows():
    msg = {"transaction_id": int(r.TransactionID), "card_id": int(r.card_id),
           "amount": float(r.TransactionAmt), "true_label": int(r.isFraud)}
    producer.send("transactions", msg)
    time.sleep(1 / RATE)

producer.flush()
print("sent", len(df), "messages")
