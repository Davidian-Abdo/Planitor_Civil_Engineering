
from collections import deque
from typing import List, Dict, Tuple, Optional, Set
import logging
import pandas as pd

class AdvancedCalendar:
    """
    Enhanced calendar system for construction scheduling with workday calculations
    and holiday support.
    """
    
    def __init__(self, start_date: pd.Timestamp, holidays: Optional[List] = None, 
                 workweek: Optional[List[int]] = None):
        """
        Initialize calendar with start date, holidays, and workweek configuration.
        
        Args:
            start_date: Project start date
            holidays: List of holiday dates
            workweek: List of workday numbers (0=Monday to 6=Sunday)
        """
        self.current_date = pd.to_datetime(start_date)
        self.holidays = set(pd.to_datetime(h) for h in (holidays or []))
        self.workweek = workweek or [0, 1, 2, 3, 4]  # Monday to Friday by default

    def is_workday(self, date: pd.Timestamp) -> bool:
        """
        Check if a date is a workday (not holiday and in workweek).
        
        Args:
            date: Date to check
            
        Returns:
            bool: True if workday, False otherwise
        """
        date_normalized = pd.to_datetime(date).normalize()
        return (date_normalized.weekday() in self.workweek and 
                date_normalized not in self.holidays)

    def add_workdays(self, start_date: pd.Timestamp, duration: int) -> pd.Timestamp:
        """
        Calculate end date by adding workdays (exclusive end).
        
        Args:
            start_date: Starting date
            duration: Number of workdays to add
            
        Returns:
            pd.Timestamp: Exclusive end date
        """
        if duration <= 0:
            return pd.to_datetime(start_date)
            
        days_counted = 0
        current_date = pd.to_datetime(start_date)
        last_workday = None
        
        while days_counted < duration:
            if self.is_workday(current_date):
                days_counted += 1
                last_workday = current_date
            current_date += timedelta(days=1)
            
        # Return exclusive end date (day after last workday)
        return pd.to_datetime(last_workday) + pd.Timedelta(days=1)
    
    def add_calendar_days(self, start_date: pd.Timestamp, days: int) -> pd.Timestamp:
        """
        Add calendar days (includes weekends/holidays) for delays.
        
        Args:
            start_date: Starting date
            days: Number of calendar days to add
            
        Returns:
            pd.Timestamp: Exclusive end date
        """
        if days <= 0:
            return pd.to_datetime(start_date)
        return pd.to_datetime(start_date) + pd.Timedelta(days=days)
