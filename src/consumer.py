import json, sqlite3, time
import requests
from kafka import KafkaConsumer

DB = "data/scores.db"
API = "http://127.0.0.1:8000/score"

con = sqlite3.connect(DB)
con.execute("""CREATE TABLE IF NOT EXISTS scores (
    transaction_id INTEGER PRIMARY KEY,
    card_id INTEGER,
    fraud_score REAL,
    alert INTEGER,
    latency_ms REAL,
    true_label INTEGER,
    scored_at REAL,
    status TEXT DEFAULT 'new',
    analyst_label INTEGER
)""")
con.commit()

consumer = KafkaConsumer(
    "transactions", bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest", consumer_timeout_ms=30000,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")))

n = 0
for m in consumer:
    tx = m.value
    out = requests.post(API, json=tx, timeout=10).json()
    con.execute(
        "INSERT OR REPLACE INTO scores (transaction_id, card_id, fraud_score, alert, latency_ms, true_label, scored_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (tx["transaction_id"], tx["card_id"], out["fraud_score"], int(out["alert"]),
         out["latency_ms"], tx.get("true_label"), time.time()))
    con.commit()
    n += 1
    if n % 20 == 0:
        print("scored", n)

print("done, scored", n, "messages")
