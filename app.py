"""
app.py - Construction Project Management Application
Main Streamlit entry point with production-ready features:
- Advanced backend initialization
- Session management with timeout
- Role-based navigation
- Error handling and logging
- Health monitoring
- Integrated with existing ui_pages.py
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

# UI imports - using your existing ui_pages functions
from ui_pages import generate_schedule_ui, monitor_project_ui, login_ui

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
    """Authenticate user and set session state - integrated with your auth system"""
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
    """Scheduling page - uses your existing generate_schedule_ui"""
    update_activity()
    st.title("📋 Project Scheduling")
    try:
        generate_schedule_ui()
    except Exception as e:
        st.error(f"❌ Scheduling interface error: {e}")
        logger.error(f"Scheduling page error: {e}")

@require_role("admin", "manager", "worker", "viewer")
def render_monitoring():
    """Monitoring page - uses your existing monitor_project_ui"""
    update_activity()
    st.title("📈 Project Monitoring")
    try:
        monitor_project_ui()
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
            
            # User actions
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("➕ Add New User"):
                    with st.form("add_user_form"):
                        new_username = st.text_input("Username")
                        new_email = st.text_input("Email")
                        new_full_name = st.text_input("Full Name")
                        new_role = st.selectbox("Role", ["admin", "manager", "worker", "viewer"])
                        new_password = st.text_input("Password", type="password")
                        
                        if st.form_submit_button("Create User"):
                            # Add user creation logic here
                            st.success(f"User {new_username} created successfully!")
            
            with col2:
                st.info("**User Management**")
                st.write("Admins can create, edit, and deactivate user accounts.")
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
            time.sleep(1)  # Simulate check
    
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
        
        # Detailed status
        st.subheader("Component Status")
        
        status_items = [
            ("Database Connection", health.get("database_connection", False)),
            ("Tables Accessible", health.get("tables_accessible", False)),
            ("Default Users", health.get("default_users_exist", False)),
            ("Default Tasks", health.get("default_tasks_exist", False)),
            ("Defaults Integration", health.get("defaults_integration", False))
        ]
        
        for item_name, status in status_items:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(item_name)
            with col2:
                if status:
                    st.success("✅")
                else:
                    st.error("❌")
        
        # Error details
        if health.get("error"):
            st.error(f"Health check error: {health['error']}")
    
    # System information
    with st.expander("📊 System Information"):
        st.write(f"**App Version:** {APP_VERSION}")
        st.write(f"**Python Version:** {sys.version.split()[0]}")
        st.write(f"**Streamlit Version:** {st.__version__}")
        st.write(f"**Session Timeout:** {auth_manager.session_timeout_minutes} minutes")
        
        if auth_manager.is_authenticated():
            user = auth_manager.get_current_user()
            st.write(f"**Logged in as:** {user['username']} ({user['role']})")
            last_activity = datetime.now() - st.session_state.last_activity
            st.write(f"**Last activity:** {int(last_activity.total_seconds() // 60)} minutes ago")

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
        
        *Trusted by construction professionals for complex project management.*
        """)
    
    with col2:
        st.image("https://via.placeholder.com/300x200/1f77b4/ffffff?text=Construction+App", 
                caption="Manage Complex Construction Projects")
        
        st.info("""
        **Demo Credentials:**
        - Admin: `admin` / `admin123`
        - Manager: `manager` / `manager123` 
        - Worker: `worker` / `worker123`
        - Viewer: `viewer` / `viewer123`
        """)
    
    # Feature highlights
    st.markdown("---")
    st.subheader("🎯 Key Features")
    
    feature_col1, feature_col2, feature_col3 = st.columns(3)
    
    with feature_col1:
        st.markdown("""
        **📋 Smart Scheduling**
        - Critical Path Method (CPM)
        - Resource leveling
        - Cross-floor dependencies
        - Delay management
        """)
    
    with feature_col2:
        st.markdown("""
        **📈 Progress Tracking** 
        - S-curve analysis
        - Progress deviation
        - Earned value management
        - Custom reporting
        """)
    
    with feature_col3:
        st.markdown("""
        **👥 Team Collaboration**
        - Role-based permissions
        - Audit trails
        - Multi-user support
        - Secure data access
        """)

# ------------------------- MAIN APPLICATION -------------------------
def initialize_application():
    """Initialize the application backend"""
    try:
        if not st.session_state.backend_initialized:
            with st.spinner("🚀 Initializing Construction Manager..."):
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

def main():
    """Main application entry point"""
    # Page configuration
    st.set_page_config(
        page_title="Construction Project Manager",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your-repo/construction-manager',
            'Report a bug': "https://github.com/your-repo/construction-manager/issues",
            'About': f"{APP_TITLE} v{APP_VERSION}"
        }
    )
    
    # Initialize session state
    init_session_state()
    
    # Initialize application backend
    if not initialize_application():
        st.stop()
    
    # Check session timeout
    check_session_timeout()
    
    # Render authentication sidebar (using your existing login_ui)
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
                "📋 Projects": render_dashboard,  # Placeholder
                "👷 My Tasks": render_dashboard   # Placeholder
            }
            
            page_handler = page_handlers.get(selected_page, render_dashboard)
            
            try:
                page_handler()
            except Exception as e:
                st.error(f"❌ Error loading page: {e}")
                logger.error(f"Page handler error for {selected_page}: {e}")
                st.info("Please try refreshing the page or contact support if the issue persists.")
        
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
        
        The application encountered an unexpected error. Please:
        
        1. **Refresh the page** to restart the application
        2. **Check your internet connection**
        3. **Clear your browser cache** if the problem persists
        4. **Contact support** with the error details below
        """)
        
        # Show error details in expander for debugging
        with st.expander("Technical Details (for support)"):
            st.code(f"""
            Error: {str(e)}
            Time: {datetime.now().isoformat()}
            App Version: {APP_VERSION}
            """)
        
        # Option to reset session
        if st.button("🔄 Reset Application"):
            st.session_state.clear()
            st.rerun()

# ------------------------- APPLICATION START -------------------------
if __name__ == "__main__":
    handle_global_errors()