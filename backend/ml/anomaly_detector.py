# backend/ml/anomaly_detector.py
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
import joblib
import os

class TransactionAnomalyDetector:
    def __init__(self, model_path='backend/ml/models/anomaly_model.pkl'):
        self.model_path = model_path
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.le = LabelEncoder()

    def train(self, df):
        """
        Train on transaction DataFrame.
        Expected columns: 'amount', 'category'
        """
        if df.empty:
            print("No data to train AnomalyDetector.")
            return

        data = df.copy()
        data['category_encoded'] = self.le.fit_transform(data['category'])
        
        X = data[['amount', 'category_encoded']]
        self.model.fit(X)
        
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({'model': self.model, 'le': self.le}, self.model_path)
        print(f"AnomalyDetector trained and saved to {self.model_path}")

    def load_model(self):
        if os.path.exists(self.model_path):
            data = joblib.load(self.model_path)
            self.model = data['model']
            self.le = data['le']
            return True
        return False

    def is_anomaly(self, amount, category):
        """
        Returns True if transaction is anomalous, False otherwise.
        """
        if not hasattr(self.le, 'classes_'):
            if not self.load_model() or not hasattr(self.le, 'classes_'):
                return False # Default to normal if no model

        try:
            # Handle unseen categories safely
            if category in self.le.classes_:
                cat_encoded = self.le.transform([category])[0]
            else:
                # Fallback for new category - map to a common one or ignore
                # For simplicity, let's map to the first class
                cat_encoded = self.le.transform([self.le.classes_[0]])[0]
            
            features = pd.DataFrame([{"amount": amount, "category_encoded": cat_encoded}])
            prediction = self.model.predict(features)
            return prediction[0] == -1
        except Exception as e:
            print(f"Error in anomaly detection: {e}")
            return False
