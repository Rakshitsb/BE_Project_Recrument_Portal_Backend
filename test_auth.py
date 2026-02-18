import sys
import os
import requests

# Add current dir to path
sys.path.insert(0, os.getcwd())

# Configuration
BASE_URL = "http://127.0.0.1:8000"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def print_result(name, success, message=""):
    if success:
        print(f"{GREEN}[PASS]{RESET} {name} {message}")
    else:
        print(f"{RED}[FAIL]{RESET} {name} {message}")


def run_tests():
    print("Running Authentication Tests...")

    # Check if server is up
    try:
        requests.get(f"{BASE_URL}/docs", timeout=2)
    except:
        print(f"{RED}Server not reachable at {BASE_URL}. Is it running?{RESET}")
        return

    # 1. Login to get token (using existing user or failing if none)
    # We'll try to signup a test user first to be safe
    test_user = {
        "name": "Test User",
        "email": "test_auth_dep@example.com",
        "password": "password123",
        "role": "USER",
    }

    # Signup
    print("Attempting signup...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/signup", json=test_user)
        if (
            resp.status_code == 200 or resp.status_code == 400
        ):  # 400 means already exists
            print_result("Signup", True)
        else:
            print_result("Signup", False, f"Status: {resp.status_code} {resp.text}")
    except Exception as e:
        print_result("Signup", False, str(e))

    # Login
    print("Attempting login...")
    token = None
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": test_user["email"], "password": test_user["password"]},
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            print_result("Login", True, f"Token: {token[:10]}...")
        else:
            print_result("Login", False, f"Status: {resp.status_code} {resp.text}")
            return
    except Exception as e:
        print_result("Login", False, str(e))
        return

    # 2. Test Protected Endpoint (Profile)
    print("Testing Protected Endpoint (/user/profile)...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/user/profile", headers=headers)

        if resp.status_code == 200:
            user_data = resp.json()
            # Verify structure
            if "id" in user_data and "role" in user_data:
                print_result("Profile Structure", True, f"Got {user_data}")
            else:
                print_result("Profile Structure", False, f"Missing fields: {user_data}")
        else:
            print_result(
                "Profile Access", False, f"Status: {resp.status_code} {resp.text}"
            )

    except Exception as e:
        print_result("Profile Access", False, str(e))


if __name__ == "__main__":
    run_tests()
