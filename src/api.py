import json, time
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, Body
from feast import FeatureStore

cols = json.load(open("models/serving_features.json"))
FEAST_COLS, MSG_COLS = cols["feast"], cols["message"]
ALL = FEAST_COLS + MSG_COLS
THRESHOLD = 0.5   # alert if score is at or above this; we tune it later

model = xgb.XGBClassifier()
model.load_model("models/xgb_serving.json")
store = FeatureStore(repo_path="feature_repo")
app = FastAPI(title="Fraud scoring service")


def score_one(tx: dict) -> dict:
    t0 = time.perf_counter()
    res = store.get_online_features(
        features=[f"card_features:{c}" for c in FEAST_COLS],
        entity_rows=[{"card_id": int(tx["card_id"])}],
    ).to_dict()
    row = {c: res[c][0] for c in FEAST_COLS}
    for c in MSG_COLS:
        row[c] = tx.get(c)
    X = pd.DataFrame([row])[ALL].astype("float64")
    p = float(model.predict_proba(X)[0, 1])
    return {
        "transaction_id": tx.get("transaction_id"),
        "fraud_score": round(p, 4),
        "alert": p >= THRESHOLD,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score")
def score(tx: dict = Body(...)):
    return score_one(tx)
