import requests
import sys

# Try to login with the generated credentials
headers = {'Content-Type': 'application/json'}
payload = {
    "phone": "9786579303", 
    "password": "demo123"
}

try:
    response = requests.post('http://127.0.0.1:5000/login', json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 200:
        print("Login SUCCESS!")
        sys.exit(0)
    else:
        print("Login FAILED!")
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
