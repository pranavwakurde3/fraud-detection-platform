# Individual Reflection: Real-Time Fraud Detection Platform

**Name:** Pranav Balasaheb Wakurde

## What I owned
I built this project from an empty folder to a working system: environment setup, EDA, feature engineering, the Feast feature store, XGBoost training with MLflow tracking, a GraphSAGE model, the Kafka producer and consumer, the FastAPI scoring service, the drift check, the Streamlit analyst dashboard, and the Docker and Kubernetes deployment of the API.

## What I learned
- **Imbalanced data:** with about 3.5% fraud, accuracy is misleading. I learned to judge models with PR-AUC and to compare against the random baseline.
- **Data leakage:** I used time-based splits and past-only features, because random splits and future information make results look better than they really are.
- **Training-serving consistency:** a feature store like Feast keeps training and live scoring on the same features. I also had to train a smaller serving model using only features available at request time.
- **Honest evaluation:** my first model scored PR-AUC 0.12. After adding more features and early stopping it reached 0.47. The GNN reached 0.29 alone and added nothing when blended, so I kept XGBoost in production and reported that result.
- **Trade-offs:** the alert threshold trades recall against false alarms (recall 0.60 at precision 0.17, versus recall 0.32 at precision 0.38), which is why the dashboard has a threshold slider.
- **Debugging real systems:** I fixed a Feast type error, a missing table after deleting a database, a Kafka container that stopped after restarts, and a Kubernetes CrashLoopBackOff caused by scikit-learn missing from the Docker image. I read the pod logs, found the cause, and added an import check to the Dockerfile so the build fails if a package is missing.

## What was hard
Getting the container to run on Kubernetes took the most time, on a slow internet connection. Large package downloads and several restarts of Docker and Minikube taught me to check each layer (image, pod, port-forward) separately.

## What I would do next
- Train the GNN longer and use separate node types for cards and devices.
- Run the consumer and dashboard on Kubernetes too.
- Use analyst feedback labels to retrain the model.
- Test the retraining path with real drift.
