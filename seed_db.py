import urllib.request
import json

def seed():
    url = "http://127.0.0.1:8000/api/v1/auth/register"
    data = {
        "badge_id": "NCB-4421",
        "full_name": "Rajesh Sharma",
        "username": "rajesh.s",
        "password": "password123",
        "rank": "inspector",
        "station_code": "MUM-WEST",
        "district": "Mumbai West",
        "state": "Maharashtra"
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            print("Status Code:", response.status)
            print("Response:", response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print("Error connecting to server:", e)

if __name__ == "__main__":
    seed()
