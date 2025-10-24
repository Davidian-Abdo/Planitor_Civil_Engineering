

import streamlit as st
import time
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Backend imports
try:
    from backend import init_backend, SessionLocal, logger, check_backend_health
    BACKEND_AVAILABLE = True
except ImportError as e:
    logger.error(f"Backend imports failed: {e}")
    BACKEND_AVAILABLE = False
from backend.auth import AuthManager, require_role
from backend.db_models import UserDB

# UI imports
from ui_pages import scheduling_page, monitoring_page, login_ui

# Scheduling imports
try:
    from scheduling_engin import run_schedule, analyze_project_progress
except ImportError:
    from scheduling_engin import run_schedule, analyze_project_progress  # Fallback for typo


    
    # Create minimal fallbacks
    def init_backend():
        return False
    
    def check_backend_health():
        return {"status": "unavailable", "error": "Backend not loaded"}
    
    SessionLocal = None

# ------------------------- CONFIGURATION -------------------------
APP_TITLE = "🏗️ Construction Project Manager Pro"
APP_VERSION = "2.1.0"

# Initialize AuthManager instance
auth_manager = AuthManager()

class AppConfig:
    """Application configuration constants"""
    SESSION_TIMEOUT_MINUTES = 150
    INIT_RETRY_ATTEMPTS = 12
    INIT_RETRY_DELAY = 2


class SessionManager:
    """Manage application session state"""
    
    @staticmethod
    def initialize_session_state():
        """Initialize all session state variables with defaults"""
        defaults = {
            "user": None,
            "logged_in": False,
            "last_activity": datetime.now(),
            "backend_initialized": False,
            "current_page": "Dashboard",
            "app_ready": False,
            "health_status": None,
            "initialization_attempts": 0
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def update_activity():
        """Update last activity timestamp"""
        if auth_manager.is_authenticated():
            st.session_state.last_activity = datetime.now()

    @staticmethod
    def check_session_timeout():
        """Check and handle session timeout"""
        if auth_manager.is_authenticated():
            elapsed = datetime.now() - st.session_state.last_activity
            timeout_minutes = AppConfig.SESSION_TIMEOUT_MINUTES
            
            if elapsed > timedelta(minutes=timeout_minutes):
                st.warning("Session timed out due to inactivity. Please log in again.")
                SessionManager.logout()
                st.rerun()

    @staticmethod
    def logout():
        """Clear user session"""
        auth_manager.logout()
        st.session_state.user = None
        st.session_state.logged_in = False
        st.session_state.current_page = "Dashboard"
        logger.info("User logged out")


class NavigationManager:
    """Handle application navigation and routing"""
    
    ROLE_PAGES = {
        "admin": ["📊 Dashboard", "📋 Scheduling", "📈 Monitoring", "👥 User Management", "⚙️ System Health"],
        "manager": ["📊 Dashboard", "📋 Scheduling", "📈 Monitoring", "📋 Projects"],
        "worker": ["📊 Dashboard", "📈 Monitoring", "👷 My Tasks"],
        "viewer": ["📊 Dashboard", "📈 Monitoring"]
    }
    
    @staticmethod
    def render_navigation() -> str:
        """Render role-based navigation sidebar"""
        if not auth_manager.is_authenticated():
            return "Dashboard"
        
        user = auth_manager.get_current_user()
        user_role = user["role"]
        
        available_pages = NavigationManager.ROLE_PAGES.get(user_role, ["📊 Dashboard"])
        
        st.sidebar.title("🧭 Navigation")
        selected_page = st.sidebar.radio("Go to", available_pages, label_visibility="collapsed")
        
        return selected_page
    
    @staticmethod
    def get_page_handler(page_name: str):
        """Get the appropriate page handler function"""
        page_handlers = {
            "📊 Dashboard": PageRenderer.render_dashboard,
            "📋 Scheduling": PageRenderer.render_scheduling,
            "📈 Monitoring": PageRenderer.render_monitoring,
            "👥 User Management": PageRenderer.render_user_management,
            "⚙️ System Health": PageRenderer.render_system_health,
            "📋 Projects": PageRenderer.render_dashboard,
            "👷 My Tasks": PageRenderer.render_dashboard
        }
        return page_handlers.get(page_name, PageRenderer.render_dashboard)


class PageRenderer:
    """Render different application pages"""
    
    @staticmethod
    @require_role("admin", "manager", "worker", "viewer")
    def render_dashboard():
        """Main dashboard page with project overview"""
        SessionManager.update_activity()
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
            except Exception:
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
                if health.get("overall_healthy"):
                    st.success("✅ All systems operational")
                else:
                    st.error("❌ System issues detected")
                
                st.json(health.get("details", {}))

    @staticmethod
    @require_role("admin", "manager")
    def render_scheduling():
        """Scheduling page"""
        SessionManager.update_activity()
        st.title("📋 Project Scheduling")
        try:
            scheduling_page()
        except Exception as e:
            st.error(f"❌ Scheduling interface error: {e}")
            logger.error(f"Scheduling page error: {e}")

    @staticmethod
    @require_role("admin", "manager", "worker", "viewer")
    def render_monitoring():
        """Monitoring page"""
        SessionManager.update_activity()
        st.title("📈 Project Monitoring")
        try:
            monitoring_page()
        except Exception as e:
            st.error(f"❌ Monitoring interface error: {e}")
            logger.error(f"Monitoring page error: {e}")

    @staticmethod
    @require_role("admin")
    def render_user_management():
        """User management page (admin only)"""
        SessionManager.update_activity()
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

    @staticmethod
    @require_role("admin")
    def render_system_health():
        """System health monitoring page"""
        SessionManager.update_activity()
        st.title("⚙️ System Health")
        
        # Run health check
        if st.button("🔄 Run Health Check", use_container_width=True):
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

    @staticmethod
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


class ApplicationInitializer:
    """Handle application initialization and backend setup"""
    
    @staticmethod
    def initialize_application() -> bool:
        """Initialize the application backend with retry logic"""
        try:
            if not st.session_state.backend_initialized:
                attempts = st.session_state.get("initialization_attempts", 0)
                
                if attempts >= AppConfig.INIT_RETRY_ATTEMPTS:
                    st.error("❌ Maximum initialization attempts reached. Please refresh the page.")
                    return False
                
                with st.spinner("🚀 Initializing Construction Manager..."):
                    # Run emergency fixes if needed
                    # -----ApplicationInitializer._run_emergency_fixes()





                    if not st.session_state.get("backend_initialized", False):
                    
                    # Initialize backend
                    success = init_backend()                    
                        if success:
                            st.session_state.backend_initialized = True
                            st.session_state.app_ready = True
                            st.session_state.health_status = check_backend_health()
                            logger.info("Application initialization completed")
                        else:
                            st.session_state.initialization_attempts = attempts + 1
                            st.warning(f"Initialization attempt {attempts + 1} failed. Retrying...")
                            time.sleep(AppConfig.INIT_RETRY_DELAY)
                            st.rerun()
                    
                        return success
            return True
            
        except Exception as e:
            st.error(f"❌ Application failed to initialize: {e}")
            logger.error(f"Application initialization failed: {e}")
            return False

    @staticmethod
    def _run_emergency_fixes():
        """Run any required emergency fixes before initialization"""
        try:
            from scripts.emergency_fix_null_duration import emergency_fix_null_duration
            if emergency_fix_null_duration():
                st.success("✅ Database constraints fixed!")
            else:
                st.error("❌ Database fix failed, but continuing...")
        except Exception as e:
            st.warning(f"⚠️ Emergency fix skipped: {e}")


class MigrationManager:
    """Handle database migration operations"""
    
    @staticmethod
    def render_migration_page():
        """Temporary migration page - remove after migration is complete"""
        st.title("🚀 Database Migration")
        
        if st.button("Run Database Migration", type="primary", use_container_width=True):
            MigrationManager._run_migration()
        
        st.info("""
        **What this migration does:**
        - Removes resource type restrictions
        - Allows NULL durations for scheduling engine
        - Creates default construction tasks
        """)

    @staticmethod
    def _run_migration():
        """Execute database migration"""
        try:
            with st.spinner("Running database migration..."):
                from backend.database_operations import check_and_migrate_database
                success = check_and_migrate_database()
                
                if success:
                    st.success("✅ Migration completed successfully!")
                    
                    # Create default tasks
                    MigrationManager._create_default_tasks()
                    st.balloons()
                else:
                    st.error("❌ Migration failed")
                    
        except Exception as e:
            st.error(f"❌ Migration error: {e}")

    @staticmethod
    def _create_default_tasks():
        """Create default tasks after migration"""
        try:
            from backend.database_operations import create_default_tasks_from_defaults_py
            with SessionLocal() as session:
                admin_user = session.query(UserDB).filter_by(username="admin").first()
                if admin_user:
                    task_count = create_default_tasks_from_defaults_py(admin_user.id)
                    st.success(f"✅ Created {task_count} default tasks!")
                else:
                    st.error("Admin user not found")
        except Exception as e:
            st.error(f"❌ Task creation failed: {e}")


class Application:
    """Main application controller"""
    
    def __init__(self):
        self.setup_page_config()
    
    def setup_page_config(self):
        """Configure Streamlit page settings"""
        st.set_page_config(
            page_title="Construction Project Manager",
            page_icon="🏗️",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def run(self):
        """Main application entry point"""
        # Initialize session state
        SessionManager.initialize_session_state()
        
        # Initialize application backend
        if not ApplicationInitializer.initialize_application():
            st.stop()
        
        # Check session timeout
        SessionManager.check_session_timeout()
        
        # Render authentication sidebar
        login_ui()
        
        # Main application logic
        if st.session_state.app_ready:
            if auth_manager.is_authenticated():
                self._render_authenticated_interface()
            else:
                # User is not logged in - show landing page
                PageRenderer.render_landing_page()
        else:
            st.error("Application not ready. Please refresh the page or check the logs.")
    
    def _render_authenticated_interface(self):
        """Render interface for authenticated users"""
        user_role = st.session_state["user"]["role"]
        
        # Admin migration button
        if user_role == "admin":
            if st.sidebar.button("🚀 Run Migration (Admin Only)", use_container_width=True):
                MigrationManager.render_migration_page()
                return
        
        # User is logged in - show navigation and pages
        selected_page = NavigationManager.render_navigation()
        st.session_state.current_page = selected_page
        
        # Render the selected page
        page_handler = NavigationManager.get_page_handler(selected_page)
        
        try:
            page_handler()
        except Exception as e:
            st.error(f"❌ Error loading page: {e}")
            logger.error(f"Page handler error for {selected_page}: {e}")


class ErrorHandler:
    """Global error handler to prevent complete app crashes"""
    
    @staticmethod
    def handle_global_errors(app_instance: Application):
        """Global error handler to prevent complete app crashes"""
        try:
            app_instance.run()
        except Exception as e:
            logger.critical(f"Application crash: {e}", exc_info=True)
            
            st.error("""
            🚨 **Application Error**
            
            The application encountered an unexpected error. Please refresh the page.
            """)
            
            if st.button("🔄 Reset Application", use_container_width=True):
                st.session_state.clear()
                st.rerun()


# ------------------------- MAIN EXECUTION -------------------------
def main():
    """Application entry point"""
    app = Application()
    ErrorHandler.handle_global_errors(app)

if __name__ == "__main__":
    main()
    


