# backend/ml/spending_predictor.py
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import os

class SpendingPredictor:
    def __init__(self, model_path='backend/ml/models/spending_model.pkl'):
        self.model_path = model_path
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.le = LabelEncoder()
        
    def train(self, df):
        """
        Train the model on a DataFrame of transactions.
        Expected columns: 'ts', 'category', 'amount'
        """
        if df.empty:
            print("No data to train SpendingPredictor.")
            return

        data = df.copy()
        data['ts'] = pd.to_datetime(data['ts'])
        data['day_of_week'] = data['ts'].dt.dayofweek
        data['day_of_month'] = data['ts'].dt.day
        data['month'] = data['ts'].dt.month
        
        # Encode category
        data['category_encoded'] = self.le.fit_transform(data['category'])
        
        features = ['day_of_week', 'day_of_month', 'month', 'category_encoded']
        X = data[features]
        y = data['amount']
        
        self.model.fit(X, y)
        
        # Save model and encoder
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({'model': self.model, 'le': self.le}, self.model_path)
        print(f"SpendingPredictor trained and saved to {self.model_path}")

    def load_model(self):
        if os.path.exists(self.model_path):
            data = joblib.load(self.model_path)
            self.model = data['model']
            self.le = data['le']
            return True
        return False


    def predict_transaction_amount(self, day_of_week, day_of_month, month, category):
        """
        Predict transaction amount for a specific scenario.
        """
        if not hasattr(self, 'model'):
             if not self.load_model():
                 return 0.0

        try:
             # Handle category encoding
             if category in self.le.classes_:
                 cat_encoded = self.le.transform([category])[0]
             else:
                 cat_encoded = self.le.transform([self.le.classes_[0]])[0] 
             
             features = pd.DataFrame([[day_of_week, day_of_month, month, cat_encoded]], 
                                     columns=['day_of_week', 'day_of_month', 'month', 'category_encoded'])
             
             prediction = self.model.predict(features)
             return float(prediction[0])
        except Exception as e:
             print(f"Prediction error: {e}")
             return 0.0
