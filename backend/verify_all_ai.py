import requests
import json

BASE_URL = "http://localhost:5000"
PHONE = "9786579303"

def heading(text):
    print(f"\n{'='*50}\n{text}\n{'='*50}")

def test_chat():
    heading("TESTING GEMINI CHAT")
    url = f"{BASE_URL}/query"
    try:
        res = requests.post(url, json={"phone": PHONE, "message": "How much did I spend on food?"})
        print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print("Chat failed:", e)

def test_prediction():
    heading("TESTING SPENDING PREDICTION")
    url = f"{BASE_URL}/api/prediction?category=Food"
    try:
        res = requests.get(url)
        print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print("Prediction failed:", e)

def test_anomalies():
    heading("TESTING ANOMALY DETECTION")
    url = f"{BASE_URL}/api/anomalies?phone={PHONE}"
    try:
        res = requests.get(url)
        data = res.json()
        print(f"Found {data.get('count')} anomalies.")
        if data.get('anomalies'):
            print("Sample anomaly:", data['anomalies'][0])
    except Exception as e:
        print("Anomaly detection failed:", e)

if __name__ == "__main__":
    test_chat()
    test_prediction()
    test_anomalies()
