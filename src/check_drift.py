import json, shutil
import numpy as np, pandas as pd, xgboost as xgb, mlflow
from scipy.stats import ks_2samp
from sklearn.metrics import average_precision_score

cols = json.load(open("models/serving_features.json"))
FEATS = cols["feast"] + cols["message"]
DRIFT_STAT = 0.10      # a feature "drifted" if its distribution moved by more than this (KS statistic)
TRIGGER_SHARE = 0.30   # retrain if more than 30% of features drifted

f = pd.read_parquet("data/features.parquet")
raw = pd.read_csv("data/train_transaction.csv", usecols=["TransactionID"] + cols["message"])
df = f.merge(raw, on="TransactionID").sort_values("event_timestamp").reset_index(drop=True)
n = len(df); a, b = int(n * 0.72), int(n * 0.80)
ref, cur = df.iloc[:a], df.iloc[b:]          # reference = training period, current = newest period

# 1) drift per feature
stats = {}
for c in FEATS:
    x, y = ref[c].dropna(), cur[c].dropna()
    stats[c] = ks_2samp(x, y).statistic if len(x) > 100 and len(y) > 100 else 0.0
drifted = [c for c, s in stats.items() if s > DRIFT_STAT]
share = len(drifted) / len(FEATS)
print(f"drifted features: {len(drifted)}/{len(FEATS)} ({share:.0%})")
print("top 5:", sorted(stats.items(), key=lambda kv: -kv[1])[:5])

# 2) Evidently HTML report (optional)
try:
    from evidently import Report, Dataset, DataDefinition
    from evidently.presets import DataDriftPreset
    dd = DataDefinition(numerical_columns=FEATS)
    r = ref[FEATS].sample(20000, random_state=1)
    c = cur[FEATS].sample(20000, random_state=1)
    snap = Report([DataDriftPreset()]).run(Dataset.from_pandas(c, data_definition=dd),
                                           Dataset.from_pandas(r, data_definition=dd))
    snap.save_html("docs/drift_report.html")
    print("saved docs/drift_report.html")
except Exception as e:
    print("Evidently report skipped:", e)

# 3) retraining trigger
mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("fraud-detection")
if share <= TRIGGER_SHARE:
    print("No retraining needed.")
else:
    print("Drift above threshold -> retraining a challenger model")
    cut = int(b * 0.9)
    tr, va = df.iloc[:cut], df.iloc[cut:b]         # train on everything before the newest period
    ratio = (tr.isFraud == 0).sum() / (tr.isFraud == 1).sum()
    cand = xgb.XGBClassifier(n_estimators=1000, max_depth=6, learning_rate=0.05, subsample=0.8,
                             colsample_bytree=0.8, scale_pos_weight=ratio, tree_method="hist",
                             eval_metric="aucpr", early_stopping_rounds=50, random_state=42)
    cand.fit(tr[FEATS], tr.isFraud, eval_set=[(va[FEATS], va.isFraud)], verbose=False)

    champ = xgb.XGBClassifier(); champ.load_model("models/xgb_serving.json")
    pr_c = average_precision_score(cur.isFraud, cand.predict_proba(cur[FEATS])[:, 1])
    pr_o = average_precision_score(cur.isFraud, champ.predict_proba(cur[FEATS])[:, 1])
    print(f"current model PR-AUC {pr_o:.4f} | challenger PR-AUC {pr_c:.4f}")

    with mlflow.start_run(run_name="auto_retrain"):
        mlflow.log_metrics({"drift_share": share, "champion_pr": pr_o, "challenger_pr": pr_c})
        if pr_c > pr_o:
            shutil.copy("models/xgb_serving.json", "models/xgb_serving_prev.json")
            cand.save_model("models/xgb_serving.json")
            mlflow.log_param("promoted", True)
            print("Challenger is better -> promoted. Restart the API to load it.")
        else:
            mlflow.log_param("promoted", False)
            print("Challenger is not better -> keeping the current model.")
