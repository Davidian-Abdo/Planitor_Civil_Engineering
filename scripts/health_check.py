#!/usr/bin/env python3
"""
Comprehensive health check for the construction management app
"""

import sys
import os
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine
from backend.db_models import BaseTaskDB, UserDB
from config.settings import settings

def health_check():
    """Run comprehensive health checks"""
    checks = {}
    
    print("🔍 Construction Manager - System Health Check")
    print("=" * 50)
    
    # Database connection check
    try:
        with SessionLocal() as session:
            session.execute("SELECT 1")
        checks["database_connection"] = "✅ Healthy"
        print("✅ Database connection: Healthy")
    except Exception as e:
        checks["database_connection"] = f"❌ Failed: {e}"
        print(f"❌ Database connection: Failed - {e}")
    
    # Table existence check
    try:
        with SessionLocal() as session:
            user_count = session.query(UserDB).count()
            task_count = session.query(BaseTaskDB).count()
        checks["database_tables"] = f"✅ Healthy (Users: {user_count}, Tasks: {task_count})"
        print(f"✅ Database tables: Healthy - {user_count} users, {task_count} tasks")
    except Exception as e:
        checks["database_tables"] = f"❌ Failed: {e}"
        print(f"❌ Database tables: Failed - {e}")
    
    # Directory permissions
    required_dirs = [settings.LOG_DIR, settings.OUTPUT_DIR, settings.TEMPLATE_DIR]
    for directory in required_dirs:
        try:
            os.makedirs(directory, exist_ok=True)
            test_file = os.path.join(directory, "test_write.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            checks[f"directory_{directory}"] = "✅ Writable"
            print(f"✅ Directory {directory}: Writable")
        except Exception as e:
            checks[f"directory_{directory}"] = f"❌ Not writable: {e}"
            print(f"❌ Directory {directory}: Not writable - {e}")
    
    # Dependencies check
    try:
        import pandas as pd
        import streamlit as st
        import plotly
        checks["python_dependencies"] = "✅ All installed"
        print("✅ Python dependencies: All installed")
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