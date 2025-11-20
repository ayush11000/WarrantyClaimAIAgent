import os
import pandas as pd
from processing import process_claims

if __name__ == "__main__":
    csv_path = os.path.join("data", "warranty_claims.csv")
    df = pd.read_csv(csv_path)
    out_df = process_claims(df.head(5))
    print(out_df[[
        "claim_id",
        "decision",
        "fraud_score",
        "policy_coverage",
        "anomaly_score",
        "risk_bucket",
        "hitl_required",
    ]])
