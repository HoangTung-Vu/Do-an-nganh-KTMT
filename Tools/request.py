import requests

api_url = "http://127.0.0.1:8000/evaluate"
data = {
    "expr": "y + x * y / x - 2*y"
}

response = requests.post(api_url, json=data)

if response.status_code == 200:
    print("Kết quả:", response.json().get("result"))
else:
    print("Lỗi:", response.json().get("error"))

# Kết quả: 0