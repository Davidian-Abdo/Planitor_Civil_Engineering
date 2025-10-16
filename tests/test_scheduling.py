import pytest
import pandas as pd
from datetime import datetime
from scheduling_engin import run_schedule, Analyze_project_progress
from helpers import parse_quantity_excel

class TestScheduling:
    def test_parse_quantity_excel(self):
        """Test parsing quantity matrix from Excel data"""
        test_data = {
            'TaskID': ['3.1', '3.2'],
            'TaskName': ['Excavation', 'Foundation'],
            'Zone_A_Floor_1': [100.0, 50.0],
            'Zone_A_Floor_2': [80.0, 40.0]
        }
        df = pd.DataFrame(test_data)
        
        result = parse_quantity_excel(df)
        
        assert '3.1' in result
        assert '3.2' in result
        assert result['3.1']['Zone_A_Floor_1'] == 100.0
        assert result['3.2']['Zone_A_Floor_2'] == 40.0

    def test_project_progress_analysis(self):
        """Test project progress analysis with sample data"""
        # Create sample reference schedule
        ref_data = {
            'Start': ['2024-01-01', '2024-01-05'],
            'End': ['2024-01-10', '2024-01-15'],
            'TaskName': ['Task A', 'Task B']
        }
        ref_df = pd.DataFrame(ref_data)
        
        # Create sample actual progress
        act_data = {
            'Date': ['2024-01-01', '2024-01-08'],
            'Progress': [0.1, 0.5]
        }
        act_df = pd.DataFrame(act_data)
        
        result = Analyze_project_progress(ref_df, act_df)
        
        assert not result.empty
        assert 'PlannedProgress' in result.columns
        assert 'CumulativeActual' in result.columns