import pytest
from backend.auth import AuthManager
from backend.db_models import UserDB

class TestAuthManager:
    def test_user_creation_and_authentication(self, test_session, sample_user_data):
        """Test user creation and authentication flow"""
        auth_manager = AuthManager(test_session)
        
        # Create user
        user = UserDB(**sample_user_data)
        test_session.add(user)
        test_session.commit()
        
        # Test authentication
        auth_user = auth_manager.authenticate("testuser", "password")
        assert auth_user is None  # Password doesn't match hash
        
        # Test with proper password hashing
        hashed_password = auth_manager.hash_password("testpassword123")
        user.hashed_password = hashed_password
        test_session.commit()
        
        auth_user = auth_manager.authenticate("testuser", "testpassword123")
        assert auth_user is not None
        assert auth_user.username == "testuser"
        assert auth_user.role == "worker"

    def test_nonexistent_user_authentication(self, test_session):
        """Test authentication with non-existent user"""
        auth_manager = AuthManager(test_session)
        result = auth_manager.authenticate("nonexistent", "password")
        assert result is None

    def test_password_hashing_consistency(self, test_session):
        """Test that password hashing produces consistent results"""
        auth_manager = AuthManager(test_session)
        password = "securepassword123"
        
        hash1 = auth_manager.hash_password(password)
        hash2 = auth_manager.hash_password(password)
        
        # Hashes should be different (due to salting) but both verify correctly
        assert hash1 != hash2
        assert auth_manager.verify_password(password, hash1)
        assert auth_manager.verify_password(password, hash2)
        assert not auth_manager.verify_password("wrongpassword", hash1)