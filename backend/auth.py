# backend/auth.py
import streamlit as st
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
import time

# Backend imports
from backend.db_models import UserDB, LoginAttemptDB
from backend.database import SessionLocal, get_db_session

logger = logging.getLogger(__name__)

# ------------------------- AUTH MANAGER -------------------------
class AuthManager:
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.session_timeout_minutes = 120  # 2 hours
        self._init_session_state()
        
    def _init_session_state(self):
        """Initialize session state with defaults"""
        if "auth_user" not in st.session_state:
            st.session_state.auth_user = None
        if "last_activity" not in st.session_state:
            st.session_state.last_activity = datetime.now()

    # ------------------------- LOGIN / LOGOUT -------------------------
    def login(self, username: str, password: str) -> dict:
        """Authenticate user with enhanced security"""
        start_time = time.time()
        
        try:
            # Input validation
            if not username or not password:
                logger.warning("Login attempt with empty credentials")
                return None
                
            username = username.strip().lower()
            
            # Check rate limiting
            if self._is_rate_limited(username):
                logger.warning(f"Rate limited login attempt for user: {username}")
                st.error("Too many login attempts. Please try again later.")
                return None

            # Database authentication
            with SessionLocal() as session:
                user = session.query(UserDB).filter(
                    func.lower(UserDB.username) == username,
                    UserDB.is_active == True
                ).first()

                if user and check_password_hash(user.hashed_password, password):
                    # Successful login
                    user_data = {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name,
                        "role": user.role,
                        "login_time": datetime.now()
                    }
                    
                    st.session_state.auth_user = user_data
                    st.session_state.last_activity = datetime.now()
                    
                    # Clear failed attempts on success
                    self._clear_failed_attempts(session, username)
                    
                    logger.info(f"Successful login for user: {username}")
                    logger.debug(f"Login completed in {time.time() - start_time:.2f}s")
                    
                    return user_data
                else:
                    # Failed login
                    self._record_failed_attempt(session, username)
                    logger.warning(f"Failed login attempt for user: {username}")
                    return None
                    
        except Exception as e:
            logger.error(f"Login error for {username}: {e}")
            return None

    def logout(self):
        """Secure logout with logging"""
        user_info = st.session_state.get("auth_user", {})
        username = user_info.get("username", "Unknown")
        st.session_state.auth_user = None
        st.session_state.last_activity = None 
        logger.info(f"User logged out: {username}")

    def _is_rate_limited(self, username: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        """Check if user is rate limited"""
        try:
            with SessionLocal() as session:
                cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
                
                attempt_count = session.query(LoginAttemptDB).filter(
                    LoginAttemptDB.username == username,
                    LoginAttemptDB.attempt_time >= cutoff_time,
                    LoginAttemptDB.successful == False
                ).count()
                return attempt_count >= max_attempts      
        except Exception as e:
            logger.error(f"Rate limit check failed for {username}: {e}")
            return False  # Fail open for availability

    def _record_failed_attempt(self, session, username: str):
        """Record failed login attempt"""
        try:
            attempt = LoginAttemptDB(
                username=username,
                successful=False,
                attempt_time=datetime.now()
            )
            session.add(attempt)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to record login attempt for {username}: {e}")
            session.rollback()

    def _clear_failed_attempts(self, session, username: str):
        """Clear failed attempts on successful login"""
        try:
            session.query(LoginAttemptDB).filter(
                LoginAttemptDB.username == username,
                LoginAttemptDB.successful == False
            ).delete()
            session.commit()
        except Exception as e:
            logger.error(f"Failed to clear login attempts for {username}: {e}")
            session.rollback()

    # ------------------------- ACCESS CONTROL -------------------------
    def require_auth(self, access_level: str = "read"):
        """
        Check authentication and authorization
        access_level: 'read', 'write', 'admin'
        """
        user = st.session_state.get("auth_user")
        
        # Check if user is logged in
        if not user:
            st.warning("🔐 Please log in to access this page.")
            st.stop()

        # Check session timeout
        last_activity = st.session_state.get("last_activity")
        if not last_activity:
            self.logout()
            st.warning("Session expired. Please log in again.")
            st.stop()
            
        if datetime.now() - last_activity > timedelta(minutes=self.session_timeout_minutes):
            self.logout()
            st.warning("🕒 Session timed out due to inactivity. Please log in again.")
            st.stop()
        # Update activity timestamp
        st.session_state.last_activity = datetime.now()
        # Check authorization based on access level
        user_role = user.get("role", "viewer")   
        role_permissions = {
            "admin": ["read", "write", "admin"],
            "manager": ["read", "write"],
            "worker": ["read", "write"], 
            "viewer": ["read"]
        }
        
        allowed_levels = role_permissions.get(user_role, ["read"])
        
        if access_level not in allowed_levels:
            st.error(f"🚫 Access denied. Your role '{user_role}' cannot perform '{access_level}' operations.")
            logger.warning(f"Authorization failed for user {user['username']}: {user_role} tried {access_level}")
            st.stop()

        return user

    def get_current_user(self):
        """Get current user data with session validation"""
        return self.require_auth("read")

    def is_authenticated(self) -> bool:
        """Check if user is authenticated without stopping execution"""
        user = st.session_state.get("auth_user")
        last_activity = st.session_state.get("last_activity")   
        if not user or not last_activity:
            return False     
        if datetime.now() - last_activity > timedelta(minutes=self.session_timeout_minutes):
            self.logout()
            return False
            
        return True

# ------------------------- ROLE-BASED DECORATOR -------------------------
def require_role(*allowed_roles):
    """
    Streamlit-compatible role-based access control decorator
    
    Usage:
        @require_role("admin", "manager")
        def sensitive_operation():
            # This function only runs for admin or manager roles
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use the global auth_manager instance
            user = auth_manager.require_auth("read")
            
            user_role = user.get("role")
            if user_role not in allowed_roles:
                st.error(f"🚫 Access denied. Required roles: {', '.join(allowed_roles)}")
                logger.warning(f"Role access denied for {user['username']} ({user_role})")
                st.stop()
                
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ------------------------- PASSWORD UTILITIES -------------------------
def hash_password(password: str) -> str:
    """Hash password with current best practices"""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    return generate_password_hash(
        password,
        method='pbkdf2:sha256',
        salt_length=16
    )
def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        return check_password_hash(hashed_password, password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False
def validate_password_strength(password: str) -> dict:
    """Validate password strength"""
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter") 
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one number")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues
    }

# ------------------------- GLOBAL INSTANCE -------------------------
# Create global instance but require session for operations
auth_manager = AuthManager()

# ------------------------- COMPATIBILITY WRAPPERS -------------------------
def login(username: str, password: str):
    """Backward compatibility wrapper"""
    return auth_manager.login(username, password)

def logout():
    """Backward compatibility wrapper""" 
    auth_manager.logout()

def require_auth(access_level: str = "read"):
    """Backward compatibility wrapper"""
    return auth_manager.require_auth(access_level)

logger.info("Authentication system initialized")
