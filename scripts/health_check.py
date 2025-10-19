#!/usr/bin/env python3
"""
Comprehensive health check - UPDATED FOR CURRENT STRUCTURE
"""

import sys
import os
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, check_database_health
from backend.db_models import UserDB, UserBaseTaskDB  # ✅ UPDATED: UserBaseTaskDB instead of BaseTaskDB

def health_check():
    """Run comprehensive health checks"""
    checks = {}
    
    print("🔍 Construction Manager - System Health Check")
    print("=" * 50)
    
    # Database connection check
    try:
        health_status = check_database_health()
        checks["database_connection"] = f"✅ {health_status['status']}"
        print(f"✅ Database connection: {health_status['status']}")
        
        # Show pool status
        pool = health_status.get('pool', {})
        print(f"   Connection pool: {pool.get('checkedin', 0)} available, {pool.get('checkedout', 0)} in use")
        
    except Exception as e:
        checks["database_connection"] = f"❌ Failed: {e}"
        print(f"❌ Database connection: Failed - {e}")
    
    # Table existence and data check
    try:
        with SessionLocal() as session:
            user_count = session.query(UserDB).count()
            task_count = session.query(UserBaseTaskDB).count()  # ✅ UPDATED
            
        checks["database_tables"] = f"✅ Healthy (Users: {user_count}, User Tasks: {task_count})"
        print(f"✅ Database tables: Healthy - {user_count} users, {task_count} user tasks")
    except Exception as e:
        checks["database_tables"] = f"❌ Failed: {e}"
        print(f"❌ Database tables: Failed - {e}")
    
    # Directory permissions check
    required_dirs = ["logs", "output", "temp"]
    for directory in required_dirs:
        try:
            os.makedirs(directory, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=directory, delete=True) as f:
                f.write(b"test")
            checks[f"directory_{directory}"] = "✅ Writable"
            print(f"✅ Directory {directory}: Writable")
        except Exception as e:
            checks[f"directory_{directory}"] = f"❌ Not writable: {e}"
            print(f"❌ Directory {directory}: Not writable - {e}")
    
    # Critical Python dependencies check
    try:
        import pandas as pd
        import streamlit as st
        import plotly
        import sqlalchemy
        checks["python_dependencies"] = "✅ All critical packages installed"
        print("✅ Python dependencies: All critical packages installed")
    except ImportError as e:
        checks["python_dependencies"] = f"❌ Missing: {e}"
        print(f"❌ Python dependencies: Missing - {e}")
    
    # Overall status
    all_healthy = all("✅" in status for status in checks.values())
    print("=" * 50)
    print(f"Overall Status: {'✅ HEALTHY' if all_healthy else '❌ UNHEALTHY'}")
    
    return all_healthy

if __name__ == "__main__":
    success = health_check()   
    sys.exit(0 if success else 1)
