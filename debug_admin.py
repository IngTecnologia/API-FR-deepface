#!/usr/bin/env python3
"""
Debug script to test admin authentication directly
"""
import requests
import json

# Test the admin login endpoint
def test_admin_login():
    url = "http://localhost:8000/admin/auth/login"
    
    # Test credentials
    credentials = {
        "email": "admin@bioentry.com",
        "password": "admin123"
    }
    
    print("Testing admin login...")
    print(f"URL: {url}")
    print(f"Credentials: {credentials}")
    
    try:
        print("Making request...")
        response = requests.post(url, json=credentials, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 401:
            print("❌ 401 Unauthorized - Authentication failed")
            try:
                error_detail = response.json()
                print(f"Error details: {error_detail}")
            except:
                print(f"Response text: {response.text}")
        elif response.status_code == 200:
            print("✅ Login successful!")
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
            except:
                print(f"Response text: {response.text}")
        else:
            print(f"Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            
        # Also test with curl-like request
        print("\n=== Testing with different credentials format ===")
        test_credentials = [
            {"email": "admin@bioentry.com", "password": "admin123"},
            {"email": " admin@bioentry.com ", "password": "admin123"},  # with spaces
            {"email": "admin@bioentry.com", "password": " admin123 "},  # with spaces
            {"email": "ADMIN@BIOENTRY.COM", "password": "admin123"},    # uppercase
        ]
        
        for creds in test_credentials:
            print(f"Testing: {creds}")
            resp = requests.post(url, json=creds, timeout=5)
            print(f"  Status: {resp.status_code}")
            if resp.status_code != 200:
                try:
                    print(f"  Error: {resp.json()}")
                except:
                    print(f"  Error: {resp.text}")
            else:
                print("  SUCCESS!")
                break
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - API server not running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_admin_login()