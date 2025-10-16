import pytest
from backend.db_models import UserDB, BaseTaskDB

class TestUserModel:
    def test_user_creation(self, test_session, sample_user_data):
        """Test basic user creation"""
        user = UserDB(**sample_user_data)
        test_session.add(user)
        test_session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.role == "worker"
        assert user.is_active == True

    def test_user_role_validation(self, test_session):
        """Test user role assignment"""
        user = UserDB(
            username="adminuser",
            email="admin@test.com",
            hashed_password="hash",
            role="admin"
        )
        test_session.add(user)
        test_session.commit()
        
        assert user.role == "admin"

class TestTaskModel:
    def test_base_task_creation(self, test_session, sample_task_data):
        """Test base task creation"""
        task = BaseTaskDB(**sample_task_data)
        test_session.add(task)
        test_session.commit()
        
        assert task.id is not None
        assert task.name == "Test Construction Task"
        assert task.discipline == "Structure"
        assert task.included == True

    def test_task_with_equipment(self, test_session):
        """Test task with equipment requirements"""
        task = BaseTaskDB(
            name="Equipment Task",
            discipline="Terrassement",
            resource_type="worker",
            task_type="equipment",
            base_duration=3.0,
            min_crews_needed=2,
            min_equipment_needed={"Excavator": 1, "Truck": 2},
            predecessors=["1.1", "1.2"]
        )
        test_session.add(task)
        test_session.commit()
        
        assert task.min_equipment_needed == {"Excavator": 1, "Truck": 2}
        assert task.predecessors == ["1.1", "1.2"]