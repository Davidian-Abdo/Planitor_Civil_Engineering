#!/usr/bin/env python3
"""
Admin user management script
Create new admin users or reset passwords
"""

import sys
import os
import getpass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import SessionLocal, AuthManager
from backend.db_models import UserDB

def create_admin_user():
    """Interactive admin user creation"""
    print("🏗️ Construction Manager - Admin User Creation")
    print("=" * 50)
    
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    full_name = input("Full name: ").strip()
    role = input("Role (admin/manager/worker/viewer): ").strip().lower()
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    if password != confirm_password:
        print("❌ Passwords do not match!")
        return False
    
    if role not in ["admin", "manager", "worker", "viewer"]:
        print("❌ Invalid role! Must be: admin, manager, worker, or viewer")
        return False
    
    try:
        with SessionLocal() as session:
            # Check if user already exists
            existing_user = session.query(UserDB).filter(
                (UserDB.username == username) | (UserDB.email == email)
            ).first()
            
            if existing_user:
                print(f"❌ User with username '{username}' or email '{email}' already exists!")
                return False
            
            # Create new user
            auth_manager = AuthManager(session)
            hashed_password = auth_manager.hash_password(password)
            
            new_user = UserDB(
                username=username,
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                role=role
            )
            
            session.add(new_user)
            session.commit()
            
            print(f"✅ User '{username}' created successfully with role '{role}'!")
            return True
            
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        return False

if __name__ == "__main__":
    create_admin_user()