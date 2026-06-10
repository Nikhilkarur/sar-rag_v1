import httpx
import subprocess
import time
import sys

BASE_URL = "http://localhost:8001/api/v1"

def wait_for_server():
    for _ in range(15):
        try:
            r = httpx.get("http://localhost:8001/health")
            if r.status_code == 200:
                print("Server is up!")
                return True
        except:
            pass
        time.sleep(1)
    return False

def test():
    if not wait_for_server():
        print("Server did not start in time.")
        return

    print("--- Testing Admin Login ---")
    with httpx.Client(base_url=BASE_URL) as client:
        r = client.post("/auth/login", json={"email": "admin@aegis-aml.com", "password": "AegisAdmin2026!"})
        print("Admin Login:", r.status_code)
        assert r.status_code == 200, r.text
        admin_token = r.json()["access_token"]
        
        print("--- Testing Admin /me ---")
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        print("Admin /me:", r.status_code)
        assert r.status_code == 200, r.text
        
        print("--- Testing Admin Verifications ---")
        r = client.get("/admin/verifications", headers={"Authorization": f"Bearer {admin_token}"})
        print("Admin Verifications:", r.status_code, len(r.json()), "items")
        assert r.status_code == 200, r.text

    print("--- Testing Tenant Login ---")
    with httpx.Client(base_url=BASE_URL) as client:
        r = client.post("/auth/login", json={"email": "demo@demofintech.com", "password": "Demo2026!"})
        print("Tenant Login:", r.status_code)
        assert r.status_code == 200, r.text
        tenant_token = r.json()["access_token"]
        
        print("--- Testing Tenant Credentials ---")
        r = client.get("/tenant/credentials", headers={"Authorization": f"Bearer {tenant_token}"})
        print("Tenant Credentials:", r.status_code, r.json())
        assert r.status_code == 200, r.text
        
        print("--- Testing Tenant Alert Queue ---")
        r = client.get("/alerts/queue", headers={"Authorization": f"Bearer {tenant_token}"})
        print("Tenant Alert Queue:", r.status_code, len(r.json()), "items")
        assert r.status_code == 200, r.text

    print("All integration tests passed successfully!")

if __name__ == "__main__":
    with open("backend_error.log", "w") as f:
        server_process = subprocess.Popen(["uvicorn", "app.main:app", "--port", "8001"], cwd=r"c:\Users\nkk77\Desktop\gsme\backend", stdout=f, stderr=f)
    try:
        test()
    finally:
        server_process.terminate()
        server_process.wait()
        with open("backend_error.log", "r") as f:
            print("\n--- SERVER LOGS ---")
            print(f.read())
