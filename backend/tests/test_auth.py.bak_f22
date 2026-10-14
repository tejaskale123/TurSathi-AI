import requests
import random
import string

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_auth_regression():
    # Generate unique emails to avoid conflicts on multiple runs
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    mobile_suffix = "".join(random.choices(string.digits, k=4))
    
    # 1. Register with mixed case email, login with lowercase
    email_reg = f"Tejas_{suffix}@Gmail.com"
    email_login = f"tejas_{suffix}@gmail.com"
    password = "SecurePassword123!"

    print("Test 1: Register and login with email casing normalization...")
    reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": "Tejas Test",
        "email": email_reg,
        "mobile_number": f"987650{mobile_suffix}",
        "password": password,
        "confirm_password": password
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"

    log_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": email_login,
        "password": password
    })
    assert log_resp.status_code == 200, f"Login failed: {log_resp.text}"
    print("Test 1 Passed!")

    # 2. Register with mobile formatting, login with normalized mobile
    mobile_reg = f"+91 987654{mobile_suffix}"
    mobile_login = f"987654{mobile_suffix}"

    print("Test 2: Register and login with mobile formatting normalization...")
    reg_resp2 = requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": "Mobile Test",
        "email": f"mobile_{suffix}@test.com",
        "mobile_number": mobile_reg,
        "password": password,
        "confirm_password": password
    })
    assert reg_resp2.status_code == 201, f"Registration failed: {reg_resp2.text}"

    log_resp2 = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": mobile_login,
        "password": password
    })
    assert log_resp2.status_code == 200, f"Login failed: {log_resp2.text}"
    print("Test 2 Passed!")

    # 3. Wrong password
    print("Test 3: Wrong password...")
    log_resp3 = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": email_login,
        "password": "WrongPassword!"
    })
    assert log_resp3.status_code == 401, f"Expected 401, got {log_resp3.status_code}"
    print("Test 3 Passed!")

    # 4. Non-existing user
    print("Test 4: Non-existing user...")
    log_resp4 = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": "nonexistent_user@example.com",
        "password": password
    })
    assert log_resp4.status_code == 401, f"Expected 401, got {log_resp4.status_code}"
    print("Test 4 Passed!")

if __name__ == "__main__":
    test_auth_regression()
    print("All regression tests passed successfully.")
