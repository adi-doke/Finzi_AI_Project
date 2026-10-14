import requests
import json

URL = "http://localhost:5000/query"
PHONE = "9786579303"

def test_query(question):
    print(f"\nAsking: {question}")
    try:
        data = {"phone": PHONE, "message": question}
        print(f"Sending data: {data}")
        res = requests.post(URL, json=data)
        
        if res.status_code == 200:
            print("Response:", json.dumps(res.json(), indent=2))
        else:
            print(f"Error {res.status_code}: {res.text}")
            
    except Exception as e:
        print("Failed to connect:", e)
        print("Note: Make sure the backend serves is running (run_backend.bat)")

if __name__ == "__main__":
    test_query("What is my bank balance?")
    test_query("Based on my recent transactions, what am I spending the most on?")
