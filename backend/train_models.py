# backend/train_models.py
import sys
import os

# Add parent directory to path to import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import Transaction
from backend.ml.spending_predictor import SpendingPredictor
from backend.ml.anomaly_detector import TransactionAnomalyDetector
import pandas as pd

def train():
    print("Fetching transaction data from database...")
    session = SessionLocal()
    
    # Fetch all transactions
    q = session.query(Transaction.ts, Transaction.category, Transaction.amount)
    data = []
    for row in q.all():
        data.append({
            'ts': row.ts,
            'category': row.category,
            'amount': float(row.amount)
        })
    session.close()
    
    df = pd.DataFrame(data)
    
    if df.empty:
        print("No transactions found in database. Please run synthetic data generation.")
        return

    print(f"Loaded {len(df)} transactions.")

    # Train Spending Predictor
    print("Training Spending Predictor...")
    predictor = SpendingPredictor()
    predictor.train(df)

    # Train Anomaly Detector
    print("Training Anomaly Detector...")
    detector = TransactionAnomalyDetector()
    detector.train(df)

    print("Model training complete.")

if __name__ == "__main__":
    train()
