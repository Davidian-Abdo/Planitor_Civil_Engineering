import pytest
from backend import SessionLocal, init_backend
from backend.db_models import UserDB, BaseTaskDB
from backend.auth import AuthManager

class TestIntegration:
    def test_full_user_workflow(self, test_session):
        """Test complete user registration and authentication workflow"""
        # Initialize auth
        auth_manager = AuthManager(test_session)
        
        # Create user
        hashed_password = auth_manager.hash_password("integration_test_123")
        user = UserDB(
            username="integration_user",
            email="integration@test.com",
            hashed_password=hashed_password,
            full_name="Integration Test User",
            role="manager"
        )
        test_session.add(user)
        test_session.commit()
        
        # Authenticate user
        auth_user = auth_manager.authenticate("integration_user", "integration_test_123")
        
        assert auth_user is not None
        assert auth_user.username == "integration_user"
        assert auth_user.role == "manager"
        
        # Create task as this user
        task = BaseTaskDB(
            name="Integration Test Task",
            discipline="Integration",
            resource_type="worker",
            task_type="worker",
            base_duration=7.0,
            min_crews_needed=3,
            creator_id=user.id,
            created_by_user=True
        )
        test_session.add(task)
        test_session.commit()
        
        assert task.id is not None
        assert task.creator_id == user.id