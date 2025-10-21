

"""
app.py - Construction Project Management Application
CORRECTED VERSION with proper imports
"""

import streamlit as st
import time
import logging
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Backend imports
from backend import init_backend, SessionLocal, logger, check_backend_health
from backend.auth import AuthManager, require_role
from backend.db_models import UserDB

# ✅ FIXED: Correct UI imports - use the functions that actually exist
from ui_pages import scheduling_page, monitoring_page, login_ui, main_ui

# ✅ FIXED: Import scheduling functions
from scheduling_engin import run_schedule, analyze_project_progress

# ------------------------- CONFIGURATION -------------------------
APP_TITLE = "🏗️ Construction Project Manager Pro"
APP_VERSION = "2.0.0"

# Initialize AuthManager instance
auth_manager = AuthManager()

# ------------------------- SESSION MANAGEMENT -------------------------
def init_session_state():
    """Initialize all session state variables with defaults"""
    defaults = {
        "user": None,
        "logged_in": False,
        "last_activity": datetime.now(),
        "backend_initialized": False,
        "current_page": "Dashboard",
        "app_ready": False,
        "health_status": None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def update_activity():
    """Update last activity timestamp - call this in all interactive functions"""
    if auth_manager.is_authenticated():
        st.session_state.last_activity = datetime.now()

def check_session_timeout():
    """Check and handle session timeout"""
    if auth_manager.is_authenticated():
        elapsed = datetime.now() - st.session_state.last_activity
        timeout_minutes = auth_manager.session_timeout_minutes
        
        if elapsed > timedelta(minutes=timeout_minutes):
            st.warning("Session timed out due to inactivity. Please log in again.")
            logout()
            st.rerun()

# ------------------------- AUTHENTICATION -------------------------
def login_user(username: str, password: str) -> bool:
    """Authenticate user and set session state"""
    try:
        user = auth_manager.login(username, password)
        
        if user:
            st.session_state.user = user
            st.session_state.logged_in = True
            st.session_state.last_activity = datetime.now()
            logger.info(f"User {username} logged in successfully")
            return True
        else:
            st.sidebar.error("❌ Invalid credentials or inactive account")
            return False
            
    except Exception as e:
        logger.error(f"Login error for {username}: {e}")
        st.sidebar.error("🔧 Login service temporarily unavailable")
        return False

def logout():
    """Clear user session"""
    auth_manager.logout()
    st.session_state.user = None
    st.session_state.logged_in = False
    st.session_state.current_page = "Dashboard"
    logger.info("User logged out")

# ------------------------- NAVIGATION -------------------------
def render_navigation():
    """Render role-based navigation sidebar"""
    if not auth_manager.is_authenticated():
        return "Dashboard"
    
    user = auth_manager.get_current_user()
    user_role = user["role"]
    
    # Define available pages based on role
    role_pages = {
        "admin": ["📊 Dashboard", "📋 Scheduling", "📈 Monitoring", "👥 User Management", "⚙️ System Health"],
        "manager": ["📊 Dashboard", "📋 Scheduling", "📈 Monitoring", "📋 Projects"],
        "worker": ["📊 Dashboard", "📈 Monitoring", "👷 My Tasks"],
        "viewer": ["📊 Dashboard", "📈 Monitoring"]
    }
    
    available_pages = role_pages.get(user_role, ["📊 Dashboard"])
    
    st.sidebar.title("🧭 Navigation")
    selected_page = st.sidebar.radio("Go to", available_pages, label_visibility="collapsed")
    
    return selected_page

# ------------------------- PAGE RENDERERS -------------------------
@require_role("admin", "manager", "worker", "viewer")
def render_dashboard():
    """Main dashboard page with project overview"""
    update_activity()
    st.title("📊 Project Dashboard")
    
    # Welcome message
    user = auth_manager.get_current_user()
    st.markdown(f"### Welcome back, {user['full_name'] or user['username']}! 👋")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        try:
            with SessionLocal() as session:
                user_count = session.query(UserDB).count()
                st.metric("Team Members", user_count)
        except:
            st.metric("Team Members", "8")
    with col2:
        st.metric("Active Projects", "3", "+1")
    with col3:
        st.metric("Tasks Today", "12", "-2")
    with col4:
        st.metric("Progress", "78%", "+5%")
    
    # Recent activity
    st.subheader("📈 Recent Activity")
    activity_col1, activity_col2 = st.columns([2, 1])
    
    with activity_col1:
        st.info("""
        **Recent Project Updates:**
        - 🟢 Foundation work completed for Zone A
        - 🟡 Electrical installation delayed by 2 days  
        - 🔵 New project 'Tower B' scheduled
        - 🟢 Safety inspection passed
        - 🔴 Material delivery delayed - follow up required
        """)
    
    with activity_col2:
        st.subheader("🚀 Quick Actions")
        if st.button("📋 New Schedule", use_container_width=True):
            st.session_state.current_page = "📋 Scheduling"
            st.rerun()
        if st.button("📈 Monitor Progress", use_container_width=True):
            st.session_state.current_page = "📈 Monitoring"
            st.rerun()
        if st.button("📊 Generate Report", use_container_width=True):
            st.sidebar.success("Report generation started...")
    
    # System status
    with st.expander("🔧 System Status"):
        if st.session_state.health_status:
            health = st.session_state.health_status
            if health["overall_healthy"]:
                st.success("✅ All systems operational")
            else:
                st.error("❌ System issues detected")
            
            st.json(health.get("details", {}))

@require_role("admin", "manager")
def render_scheduling():
    """Scheduling page - uses your existing scheduling_page"""
    update_activity()
    st.title("📋 Project Scheduling")
    try:
        # ✅ FIXED: Use scheduling_page instead of generate_schedule_ui
        scheduling_page()
    except Exception as e:
        st.error(f"❌ Scheduling interface error: {e}")
        logger.error(f"Scheduling page error: {e}")

@require_role("admin", "manager", "worker", "viewer")
def render_monitoring():
    """Monitoring page - uses your existing monitoring_page"""
    update_activity()
    st.title("📈 Project Monitoring")
    try:
        # ✅ FIXED: Use monitoring_page instead of monitor_project_ui
        monitoring_page()
    except Exception as e:
        st.error(f"❌ Monitoring interface error: {e}")
        logger.error(f"Monitoring page error: {e}")

@require_role("admin")
def render_user_management():
    """User management page (admin only)"""
    update_activity()
    st.title("👥 User Management")
    
    try:
        with SessionLocal() as session:
            users = session.query(UserDB).all()
        
        if users:
            user_data = []
            for user in users:
                user_data.append({
                    "ID": user.id,
                    "Username": user.username,
                    "Email": user.email,
                    "Full Name": user.full_name or "N/A",
                    "Role": user.role,
                    "Status": "🟢 Active" if user.is_active else "🔴 Inactive",
                    "Created": user.created_at.strftime("%Y-%m-%d")
                })
            
            st.dataframe(user_data, use_container_width=True)
        else:
            st.info("No users found in the system.")
            
    except Exception as e:
        st.error(f"❌ User management error: {e}")
        logger.error(f"User management error: {e}")

@require_role("admin")
def render_system_health():
    """System health monitoring page"""
    update_activity()
    st.title("⚙️ System Health")
    
    # Run health check
    if st.button("🔄 Run Health Check"):
        with st.spinner("Checking system health..."):
            health_status = check_backend_health()
            st.session_state.health_status = health_status
            time.sleep(1)
    
    health = st.session_state.health_status or {}
    
    if health:
        # Overall status
        col1, col2 = st.columns([1, 3])
        with col1:
            if health.get("overall_healthy"):
                st.success("✅ **System Healthy**")
            else:
                st.error("❌ **System Issues**")
        
        with col2:
            st.metric("Users", health.get("details", {}).get("user_count", "N/A"))
            st.metric("Tasks", health.get("details", {}).get("task_count", "N/A"))
    
    # System information
    with st.expander("📊 System Information"):
        st.write(f"**App Version:** {APP_VERSION}")
        st.write(f"**Python Version:** {sys.version.split()[0]}")
        st.write(f"**Streamlit Version:** {st.__version__}")
        
        if auth_manager.is_authenticated():
            user = auth_manager.get_current_user()
            st.write(f"**Logged in as:** {user['username']} ({user['role']})")

def render_landing_page():
    """Professional landing page for non-authenticated users"""
    st.title(APP_TITLE)
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## 🏗️ Professional Construction Project Management
        
        **Streamline your construction projects with enterprise-grade features:**
        
        ✅ **Advanced Scheduling** - Multi-zone, multi-floor project planning with CPM  
        ✅ **Resource Optimization** - Smart allocation of workers and equipment  
        ✅ **Progress Monitoring** - Real-time S-curve analysis and deviation tracking  
        ✅ **Role-Based Access** - Secure collaboration for your entire team  
        ✅ **French Standards** - Built for French construction industry requirements  
        """)
    
    with col2:
        st.info("""
        **Demo Credentials:**
        - Admin: `admin` / `admin123`
        - Manager: `manager` / `manager123` 
        - Worker: `worker` / `worker123`
        - Viewer: `viewer` / `viewer123`
        """)

# ------------------------- MAIN APPLICATION -------------------------
def initialize_application():
    """Initialize the application backend"""
    try:
        if not st.session_state.backend_initialized:
            with st.spinner("🚀 Initializing Construction Manager..."):
                # ✅ NEW: Run index fix before initialization
                try:
                    from fix_indexes import drop_problematic_indexes
                    drop_problematic_indexes()
                    logger.info("✅ Duplicate indexes cleaned up")
                except Exception as e:
                    logger.warning(f"⚠️ Index cleanup skipped: {e}")
                init_backend()
                st.session_state.backend_initialized = True
                st.session_state.app_ready = True
                
                # Initial health check
                st.session_state.health_status = check_backend_health()
                
                logger.info("Application initialization completed")
                return True
        return True
    except Exception as e:
        st.error(f"❌ Application failed to initialize: {e}")
        logger.error(f"Application initialization failed: {e}")
        return False


def migration_page():
    """Temporary migration page - remove after migration is complete"""
    st.title("🚀 Database Migration")
    
    if st.button("Run Database Migration", type="primary"):
        try:
            with st.spinner("Running database migration..."):
                from backend.database_operations import check_and_migrate_database
                success = check_and_migrate_database()
                
                if success:
                    st.success("✅ Migration completed successfully!")
                    st.balloons()
                    
                    # Create default tasks
                    from backend.database_operations import create_default_tasks_from_defaults_py
                    from backend.database import SessionLocal
                    from backend.db_models import UserDB
                    
                    with SessionLocal() as session:
                        admin_user = session.query(UserDB).filter_by(username="admin").first()
                        if admin_user:
                            task_count = create_default_tasks_from_defaults_py(admin_user.id)
                            st.success(f"✅ Created {task_count} default tasks!")
                        else:
                            st.error("Admin user not found")
                else:
                    st.error("❌ Migration failed")
                    
        except Exception as e:
            st.error(f"❌ Migration error: {e}")
    
    st.info("""
    **What this migration does:**
    - Removes resource type restrictions
    - Allows NULL durations for scheduling engine
    - Creates default construction tasks
    """)

  

def main():
    """Main application entry point"""
    # Page configuration
    st.set_page_config(
        page_title="Construction Project Manager",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Initialize application backend
    if not initialize_application():
        st.stop()

    # ✅ TEMPORARY: Add migration page for admin
    user_role = st.session_state["user"]["role"]
    if user_role == "admin" and st.sidebar.button("🚀 Run Migration (Admin Only)"):
        migration_page()
        return
    # Check session timeout
    check_session_timeout()
    
    # Render authentication sidebar
    login_ui()
    
    # Main application logic
    if st.session_state.app_ready:
        if auth_manager.is_authenticated():
            # User is logged in - show navigation and pages
            selected_page = render_navigation()
            st.session_state.current_page = selected_page
            
            # Render the selected page
            page_handlers = {
                "📊 Dashboard": render_dashboard,
                "📋 Scheduling": render_scheduling,
                "📈 Monitoring": render_monitoring,
                "👥 User Management": render_user_management,
                "⚙️ System Health": render_system_health,
                "📋 Projects": render_dashboard,
                "👷 My Tasks": render_dashboard
            }
            
            page_handler = page_handlers.get(selected_page, render_dashboard)
            
            try:
                page_handler()
            except Exception as e:
                st.error(f"❌ Error loading page: {e}")
                logger.error(f"Page handler error for {selected_page}: {e}")
        
        else:
            # User is not logged in - show landing page
            render_landing_page()
    
    else:
        st.error("Application not ready. Please refresh the page or check the logs.")

# ------------------------- ERROR BOUNDARY -------------------------
def handle_global_errors():
    """Global error handler to prevent complete app crashes"""
    try:
        main()
    except Exception as e:
        logger.critical(f"Application crash: {e}", exc_info=True)
        
        st.error("""
        🚨 **Application Error**
        
        The application encountered an unexpected error. Please refresh the page.
        """)
        
        if st.button("🔄 Reset Application"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    handle_global_errors()
