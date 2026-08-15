from src.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/api/v1/status")
print("STATUS_CODE:", response.status_code)
try:
    print("RESPONSE:", response.json())
except Exception:
    print("RESPONSE TEXT:", response.text)

print("ALL_ROUTES:")
for route in app.routes:
    print(f"Path: {route.path}, Name: {route.name}, Methods: {getattr(route, 'methods', None)}")
