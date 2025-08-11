#!/usr/bin/env python3
"""
Test admin authentication logic directly without FastAPI
"""
import bcrypt
import json
import os

# Test the password verification logic
def test_password_verification():
    print("=== Testing Password Verification Logic ===")
    
    # Test data
    test_password = "admin123"
    stored_hash = "$2b$12$AnMT8Wwq.lp4uaKGiNhknO95xUo2Kk37zOmpMQhkCAJsMuH0IIxvG"
    
    print(f"Password: {test_password}")
    print(f"Stored hash: {stored_hash}")
    
    # Test bcrypt verification
    try:
        is_valid = bcrypt.checkpw(test_password.encode('utf-8'), stored_hash.encode('utf-8'))
        print(f"bcrypt.checkpw result: {is_valid}")
        
        if is_valid:
            print("✅ Password verification SUCCESS")
        else:
            print("❌ Password verification FAILED")
            return False
    except Exception as e:
        print(f"❌ bcrypt error: {e}")
        return False
    
    return True

def test_admin_users_file():
    print("\n=== Testing Admin Users File ===")
    
    admin_file = "data/admin_users.json"
    print(f"File path: {admin_file}")
    
    if not os.path.exists(admin_file):
        print("❌ Admin users file does not exist")
        return False
    
    try:
        with open(admin_file, 'r') as f:
            users = json.load(f)
        
        print(f"✅ File loaded successfully")
        print(f"Number of users: {len(users)}")
        
        # Find admin user
        admin_user = None
        for user in users:
            if user["email"] == "admin@bioentry.com":
                admin_user = user
                break
        
        if not admin_user:
            print("❌ Admin user not found")
            return False
        
        print("✅ Admin user found:")
        print(f"  Email: {admin_user['email']}")
        print(f"  Active: {admin_user['activo']}")
        print(f"  Role: {admin_user['rol']}")
        
        # Test password hash from file
        file_hash = admin_user['password_hash']
        print(f"  Hash from file: {file_hash}")
        
        is_valid = bcrypt.checkpw("admin123".encode('utf-8'), file_hash.encode('utf-8'))
        print(f"  Password valid: {is_valid}")
        
        if not is_valid:
            print("❌ Password hash in file is invalid")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def test_manual_authentication():
    print("\n=== Manual Authentication Test ===")
    
    # Simulate the authentication logic from admin_auth.py
    email = "admin@bioentry.com"
    password = "admin123"
    
    # Load users
    try:
        with open("data/admin_users.json", 'r') as f:
            users = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load users: {e}")
        return False
    
    # Find user
    user_data = None
    for user in users:
        if user["email"] == email and user["activo"]:
            user_data = user
            break
    
    if not user_data:
        print(f"❌ User not found or not active: {email}")
        return False
    
    print(f"✅ User found: {email}")
    
    # Verify password
    try:
        is_valid = bcrypt.checkpw(password.encode('utf-8'), user_data["password_hash"].encode('utf-8'))
        if is_valid:
            print("✅ Authentication would succeed")
            return True
        else:
            print("❌ Authentication would fail - wrong password")
            return False
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False

if __name__ == "__main__":
    success = True
    
    # Run all tests
    success &= test_password_verification()
    success &= test_admin_users_file()
    success &= test_manual_authentication()
    
    print(f"\n=== FINAL RESULT ===")
    if success:
        print("✅ All authentication tests PASSED")
        print("The login should work. Check for other issues (CORS, endpoint routing, request format)")
    else:
        print("❌ Authentication tests FAILED")
        print("There are issues with the authentication logic or data")