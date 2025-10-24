import pandas as pd
import tempfile
import os
import time
import shutil
import datetime
from datetime import timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import List, Dict, Optional, Tuple, Set, Any
import bisect
import math
import warnings
import logging
from io import BytesIO
from utils.scheduler import AdvancedScheduler
# Streamlit for UI components
import streamlit as st
import plotly.express as px

# Database imports
from backend.database import SessionLocal
from backend.db_models import UserBaseTaskDB

# Model imports
from models import Task, BaseTask, WorkerResource, EquipmentResource
from defaults import workers, equipment, BASE_TASKS, cross_floor_links, acceleration, SHIFT_CONFIG, disciplines

# Helper imports
from helpers import (
    ResourceAllocationList, AdvancedResourceManager, EquipmentResourceManager,
    Topo_order_tasks, generate_tasks, validate_tasks
)

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

# Constants
GROUND_DISCIPLINES = ["Préliminaire", "Terrassement", "Fondations"]
MAX_SCHEDULING_ATTEMPTS = 10000
MAX_FORWARD_ATTEMPTS = 3000


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


class DurationCalculator:
    """
    Calculate task durations based on resources, quantities, and productivity rates.
    """
    
    def __init__(self, workers: Dict[str, WorkerResource], 
                 equipment: Dict[str, EquipmentResource], 
                 quantity_matrix: Dict):
        self.workers = workers
        self.equipment = equipment
        self.quantity_matrix = quantity_matrix
        self.acceleration = acceleration

    def _get_quantity(self, task: Task) -> float:
        """
        Get quantity for task from quantity matrix with comprehensive fallback handling.
        
        Args:
            task: Task to get quantity for
            
        Returns:
            float: Task quantity
        """
        try:
            base_q = self.quantity_matrix.get(str(task.base_id), {})
            floor_q = base_q.get(task.floor, {})
            
            if not floor_q:
                logger.warning(f"⚠️ Floor {task.floor} for task {task.base_id} not found in quantity_matrix")
                qty = getattr(task, 'quantity', 1.0)
            else:
                qty = floor_q.get(task.zone, getattr(task, 'quantity', 1.0))
            
            # Validate quantity
            if qty is None or qty <= 0:
                logger.warning(f"⚠️ Invalid quantity {qty} for task {task.base_id}, defaulting to 1")
                qty = 1.0
            
            logger.debug(f"✅ Task {task.base_id}, floor {task.floor} quantity: {qty}")
            task.quantity = qty
            return float(qty)
            
        except Exception as e:
            logger.error(f"❌ Error getting quantity for task {task.base_id}: {e}")
            return 1.0

    def _get_productivity_rate(self, resource, task_id: str, default: float = 1.0) -> float:
        """
        Get task-specific productivity rate from resource.
        
        Args:
            resource: Worker or equipment resource
            task_id: Task identifier
            default: Default productivity rate
            
        Returns:
            float: Productivity rate
        """
        try:
            if hasattr(resource, 'productivity_rates'):
                if isinstance(resource.productivity_rates, dict):
                    return resource.productivity_rates.get(task_id, default)
                return resource.productivity_rates
            return default
        except Exception:
            return default

    def _get_first_equipment_type(self, min_equipment_needed: Dict) -> Optional[str]:
        """
        Get the first equipment type from min_equipment_needed dictionary.
        
        Args:
            min_equipment_needed: Dictionary of equipment requirements
            
        Returns:
            Optional[str]: First equipment type
        """
        if not min_equipment_needed:
            return None
        
        first_key = next(iter(min_equipment_needed))
        
        if isinstance(first_key, (tuple, list)):
            return first_key[0] if first_key else None
        return first_key

    def _calculate_worker_duration(self, task: Task, crews: int, qty: float) -> float:
        """Calculate duration for worker-only tasks."""
        if task.resource_type not in self.workers:
            raise ValueError(f"Worker resource '{task.resource_type}' not found for task {task.id}")
        
        resource = self.workers[task.resource_type]
        base_prod = self._get_productivity_rate(resource, task.base_id, 1.0)
        daily_prod = base_prod * crews
        
        if daily_prod <= 0:
            raise ValueError(f"Non-positive worker productivity for {task.id}")
            
        return qty / daily_prod

    def _calculate_equipment_duration(self, task: Task, eq_alloc: Dict, qty: float) -> float:
        """Calculate duration for equipment-only tasks."""
        if not eq_alloc:
            raise ValueError(f"Equipment task {task.id} has no equipment specified")
        
        first_eq_type = self._get_first_equipment_type(task.min_equipment_needed)
        if not first_eq_type:
            raise ValueError(f"No equipment types found for task {task.id}")
        
        # Calculate total units for first equipment type
        total_units = 0
        if isinstance(first_eq_type, (tuple, list)):
            for eq_name in first_eq_type:
                total_units += eq_alloc.get(eq_name, 0)
        else:
            total_units = eq_alloc.get(first_eq_type, 0)
        
        if first_eq_type not in self.equipment:
            raise ValueError(f"Equipment '{first_eq_type}' not found for task {task.id}")
        
        resource = self.equipment[first_eq_type]
        base_prod = self._get_productivity_rate(resource, task.base_id, 1.0)
        daily_prod_total = base_prod * total_units
        
        if daily_prod_total <= 0:
            raise ValueError(f"Non-positive equipment productivity for {task.id}")
            
        return qty / daily_prod_total

    def _calculate_hybrid_duration(self, task: Task, crews: int, eq_alloc: Dict, qty: float) -> float:
        """Calculate duration for hybrid tasks (both workers and equipment)."""
        # Worker calculation
        if task.resource_type not in self.workers:
            raise ValueError(f"Worker resource '{task.resource_type}' not found for task {task.id}")
            
        worker_res = self.workers[task.resource_type]
        base_prod_worker = self._get_productivity_rate(worker_res, task.base_id, 1.0)
        daily_worker_prod = base_prod_worker * crews
        
        if daily_worker_prod <= 0:
            raise ValueError(f"Non-positive worker productivity for {task.id}")

        # Equipment calculation
        daily_equip_prod = 0
        if eq_alloc:
            first_eq_type = self._get_first_equipment_type(task.min_equipment_needed)
            if first_eq_type and first_eq_type in self.equipment:
                total_units = 0
                if isinstance(first_eq_type, (tuple, list)):
                    for eq_name in first_eq_type:
                        total_units += eq_alloc.get(eq_name, 0)
                else:
                    total_units = eq_alloc.get(first_eq_type, 0)
                
                eq_res = self.equipment[first_eq_type]
                base_prod_eq = self._get_productivity_rate(eq_res, task.base_id, 1.0)
                daily_equip_prod = base_prod_eq * total_units * getattr(eq_res, 'efficiency', 1.0)
        
        # Use bottleneck (longer duration)
        duration_worker = qty / daily_worker_prod if daily_worker_prod > 0 else float('inf')
        duration_equip = qty / daily_equip_prod if daily_equip_prod > 0 else float('inf')
        
        return max(duration_worker, duration_equip)

    def calculate_duration(self, task: Task, allocated_crews: int = None, 
                          allocated_equipments: dict = None) -> int:
        """
        Calculate workdays using actual allocated resources.
        
        Args:
            task: Task to calculate duration for
            allocated_crews: Number of crews allocated
            allocated_equipments: Equipment allocations
            
        Returns:
            int: Duration in workdays (rounded up)
        """
        # Return fixed duration if specified
        if getattr(task, "base_duration", None) is not None:
            return int(math.ceil(task.base_duration))
            
        # Get quantity and normalize allocations
        qty = self._get_quantity(task)
        crews = allocated_crews if allocated_crews is not None else max(1, task.min_crews_needed)
        eq_alloc = allocated_equipments if allocated_equipments is not None else (task.min_equipment_needed or {})

        # Calculate base duration based on task type
        if task.task_type == "worker":
            duration = self._calculate_worker_duration(task, crews, qty)
        elif task.task_type == "equipment":
            duration = self._calculate_equipment_duration(task, eq_alloc, qty)
        elif task.task_type == "hybrid":
            duration = self._calculate_hybrid_duration(task, crews, eq_alloc, qty)
        else:
            raise ValueError(f"Unknown task_type: {task.task_type}")

        # Apply shift factors and optimization
        shift_factor = SHIFT_CONFIG.get(task.discipline, SHIFT_CONFIG.get("default", 1.0))
        duration = duration / shift_factor
        
        # Apply floor acceleration (experience factor)
        if task.floor > 1:
            duration *= 0.98 ** (task.floor - 1)

        # Validate and finalize duration
        if not isinstance(duration, (int, float)) or math.isnan(duration) or math.isinf(duration):
            raise ValueError(f"Invalid duration for task {task.id}: {duration!r}")

        duration = float(duration)
        if duration <= 0:
            logger.warning(f"Non-positive duration for task {task.id}. Setting to 1 day.")
            duration = 1.0

        duration_days = int(math.ceil(duration))
        logger.debug(f"Task {task.id} duration: {duration_days} days")
        
        return max(1, duration_days)


class CPMAnalyzer:
    """
    Critical Path Method analyzer for project scheduling.
    """
    
    def __init__(self, tasks, durations=None, dependencies=None):
        """
        Initialize CPM analyzer with tasks and dependencies.
        
        Args:
            tasks: List of tasks or task IDs
            durations: Dictionary of task durations (if tasks are IDs)
            dependencies: Dictionary of task dependencies (if tasks are IDs)
        """
        # Case A: List of Task objects
        if durations is None and dependencies is None and tasks and hasattr(tasks[0], "id"):
            self.tasks = tasks
            self.task_by_id = {t.id: t for t in tasks}
            self.durations = {t.id: t.base_duration for t in tasks}
            self.dependencies = {t.id: t.predecessors for t in tasks}
        # Case B: Raw IDs with dictionaries
        else:
            self.tasks = tasks
            self.task_by_id = {tid: None for tid in tasks}
            self.durations = durations
            self.dependencies = dependencies

        # Graph structures
        self.adj = defaultdict(list)      # Successors
        self.rev_adj = defaultdict(list)  # Predecessors  
        self.indeg = defaultdict(int)     # In-degree
        self.outdeg = defaultdict(int)    # Out-degree

        # CPM results
        self.ES, self.EF = {}, {}  # Earliest Start/Finish
        self.LS, self.LF = {}, {}  # Latest Start/Finish  
        self.float = {}            # Float/Slack
        self.project_duration = 0

    def build_graph(self):
        """Build task dependency graph."""
        for tid in self.tasks:
            preds = self.dependencies.get(tid, [])
            for pred in preds:
                self.adj[pred].append(tid)
                self.rev_adj[tid].append(pred)
                self.indeg[tid] += 1
                self.outdeg[pred] += 1

    def forward_pass(self):
        """Compute earliest start and finish times."""
        queue = deque([tid for tid in self.tasks if self.indeg[tid] == 0])
        
        while queue:
            current = queue.popleft()
            preds = self.dependencies.get(current, [])
            
            # Earliest start is max of predecessor finishes
            self.ES[current] = max((self.EF[p] for p in preds), default=0)
            self.EF[current] = self.ES[current] + self.durations[current]
            
            # Update successors
            for successor in self.adj[current]:
                self.indeg[successor] -= 1
                if self.indeg[successor] == 0:
                    queue.append(successor)
                    
        self.project_duration = max(self.EF.values()) if self.EF else 0

    def backward_pass(self):
        """Compute latest start and finish times."""
        if not self.EF:
            raise ValueError("Must run forward pass before backward pass")
            
        queue = deque([tid for tid in self.tasks if self.outdeg[tid] == 0])
        
        for tid in queue:
            self.LF[tid] = self.project_duration
            self.LS[tid] = self.LF[tid] - self.durations[tid]

        while queue:
            current = queue.popleft()
            for predecessor in self.rev_adj[current]:
                if predecessor not in self.LF:
                    self.LF[predecessor] = self.LS[current]
                else:
                    self.LF[predecessor] = min(self.LF[predecessor], self.LS[current])
                    
                self.LS[predecessor] = self.LF[predecessor] - self.durations[predecessor]
                self.outdeg[predecessor] -= 1
                
                if self.outdeg[predecessor] == 0:
                    queue.append(predecessor)

    def calculate_float(self):
        """Calculate float/slack for all tasks."""
        for tid in self.tasks:
            self.float[tid] = self.LS[tid] - self.ES[tid]

    def analyze(self):
        """Run full CPM analysis."""
        self.build_graph()
        self.forward_pass()
        self.backward_pass()
        self.calculate_float()
        return self.project_duration

    def get_critical_tasks(self) -> List[str]:
        """Get list of critical task IDs (zero float)."""
        return [tid for tid in self.tasks if self.float.get(tid, 0) == 0]

    def get_critical_paths(self) -> List[List[str]]:
        """Find all critical paths in the project."""
        critical_paths = []

        def depth_first_search(path: List[str]):
            """Recursive DFS to find critical paths."""
            last_task = path[-1]
            extended = False
            
            for successor in self.adj[last_task]:
                if self.float.get(successor, 0) == 0:
                    depth_first_search(path + [successor])
                    extended = True
                    
            if not extended:
                critical_paths.append(path)

        # Start from tasks with no predecessors that are critical
        for tid in self.tasks:
            if not self.dependencies.get(tid) and self.float.get(tid, 0) == 0:
                depth_first_search([tid])

        return critical_paths

    def run(self):
        """Convenience method to run full analysis."""
        self.analyze()
        return self


# Database and User Task Functions
def get_user_tasks_for_scheduling(user_id: int) -> Dict[str, List[Dict]]:
    """
    Get user's tasks organized by discipline for scheduling.
    
    Args:
        user_id: User ID to get tasks for
        
    Returns:
        Dictionary of tasks organized by discipline
    """
    try:
        with SessionLocal() as session:
            user_tasks = session.query(UserBaseTaskDB).filter(
                UserBaseTaskDB.user_id == user_id,
                UserBaseTaskDB.included == True
            ).all()
            return organize_user_tasks_by_discipline(user_tasks)
    except Exception as e:
        logger.error(f"Error loading user tasks for user {user_id}: {e}")
        return {}

def organize_user_tasks_by_discipline(user_tasks: List[UserBaseTaskDB]) -> Dict[str, List[Dict]]:
    """
    Convert user tasks to format expected by generate_tasks_hybrid.
    
    Args:
        user_tasks: List of user tasks from database
        
    Returns:
        Dictionary of tasks organized by discipline
    """
    tasks_by_discipline = {}
    
    for task in user_tasks:
        if task.discipline not in tasks_by_discipline:
            tasks_by_discipline[task.discipline] = []
        
        task_dict = {
            'id': task.id,
            'name': task.name,
            'discipline': task.discipline,
            'resource_type': task.resource_type,
            'base_duration': task.base_duration,
            'min_crews_needed': task.min_crews_needed,
            'min_equipment_needed': task.min_equipment_needed or {},
            'predecessors': task.predecessors or [],
            'repeat_on_floor': task.repeat_on_floor,
            'included': task.included,
            'delay': task.delay,
            'cross_floor_dependencies': task.cross_floor_dependencies or [],
            'applies_to_floors': task.applies_to_floors,
            'cross_floor_repetition': getattr(task, 'cross_floor_repetition', True),
            'task_type': getattr(task, 'task_type', 'worker')
        }
        tasks_by_discipline[task.discipline].append(task_dict)
        
    return tasks_by_discipline


def run_schedule(zone_floors: Dict, quantity_matrix: Dict, start_date: pd.Timestamp,
                 workers_dict: Optional[Dict] = None, equipment_dict: Optional[Dict] = None,
                 holidays: Optional[List] = None, discipline_zone_cfg: Optional[Dict] = None,
                 base_tasks_override: Optional[Dict] = None, user_id: Optional[int] = None) -> Tuple[Dict, str]:
    """
    Run scheduling with HYBRID approach and enhanced error handling.
    
    Args:
        zone_floors: Dictionary of zones and their floor counts
        quantity_matrix: Task quantities by zone and floor
        start_date: Project start date
        workers_dict: Worker resources (uses defaults if None)
        equipment_dict: Equipment resources (uses defaults if None)
        holidays: List of holiday dates
        discipline_zone_cfg: Discipline-zone configuration
        base_tasks_override: Override tasks for scheduling
        user_id: User ID for user-specific tasks
        
    Returns:
        Tuple of (schedule, output_folder)
    """
    from reporting import BasicReporter
    
    try:
        # Use provided resources or defaults
        workers_used = workers_dict if workers_dict else workers
        equipment_used = equipment_dict if equipment_dict else equipment
        
        # Determine which tasks to use
        if base_tasks_override is not None:
            base_tasks_to_use = base_tasks_override
            logger.info("✅ Using provided user tasks")
        elif user_id is not None:
            base_tasks_to_use = get_user_tasks_for_scheduling(user_id)
            logger.info(f"✅ Using tasks for user: {user_id}")
        else:
            base_tasks_to_use = BASE_TASKS
            logger.info("✅ Using default tasks")
        
        # Generate tasks
        tasks = generate_tasks(
            base_tasks_to_use, 
            zone_floors, 
            cross_floor_links,
            discipline_zone_cfg=discipline_zone_cfg
        )

        # Validate and patch task data
        tasks, workers_used, equipment_used, quantity_matrix = validate_tasks(
            tasks, workers_used, equipment_used, quantity_matrix
        )

        # Initialize calendar and duration calculator
        workweek = [0, 1, 2, 3, 4, 5]  # Monday to Saturday
        start_date = pd.Timestamp(start_date)
        calendar = AdvancedCalendar(start_date=start_date, holidays=holidays, workweek=workweek)
        duration_calc = DurationCalculator(workers_used, equipment_used, quantity_matrix)

        # Run scheduler
        scheduler = AdvancedScheduler(tasks, workers_used, equipment_used, calendar, duration_calc)
        schedule = scheduler.generate()

        # Generate reports
        reporter = BasicReporter(tasks, schedule, scheduler.worker_manager, 
                               scheduler.equipment_manager, calendar)
        output_folder = reporter.export_all()

        return schedule, output_folder
        
    except Exception as e:
        logger.error(f"❌ Schedule generation failed: {e}")
        raise


def analyze_project_progress(reference_df: pd.DataFrame, actual_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute planned vs actual progress time series and deviations.
    
    Args:
        reference_df: Reference schedule DataFrame
        actual_df: Actual progress DataFrame
        
    Returns:
        DataFrame with progress analysis
    """
    # Create defensive copies
    ref_df = reference_df.copy()
    act_df = actual_df.copy()

    # Validate reference DataFrame
    for required_col in ("Start", "End"):
        if required_col not in ref_df.columns:
            raise ValueError(f"Reference schedule missing required column '{required_col}'")

    # Parse dates
    ref_df["Start"] = pd.to_datetime(ref_df["Start"], errors="coerce")
    ref_df["End"] = pd.to_datetime(ref_df["End"], errors="coerce")
    
    if ref_df["Start"].isna().all() or ref_df["End"].isna().all():
        raise ValueError("Reference schedule dates could not be parsed.")

    # Build timeline
    timeline_start = ref_df["Start"].min()
    timeline_end = ref_df["End"].max()
    
    if pd.isna(timeline_start) or pd.isna(timeline_end):
        raise ValueError("Reference schedule dates invalid.")

    timeline = pd.date_range(timeline_start.normalize(), timeline_end.normalize(), freq="D")

    # Calculate planned progress curve
    planned_data = []
    total_tasks = max(1, len(ref_df))
    
    for day in timeline:
        ongoing_tasks = ref_df[
            (ref_df["Start"].dt.normalize() <= day) & 
            (ref_df["End"].dt.normalize() >= day)
        ]
        planned_progress = len(ongoing_tasks) / total_tasks
        planned_data.append({"Date": day, "PlannedProgress": planned_progress})

    planned_df = pd.DataFrame(planned_data)
    planned_df["Date"] = pd.to_datetime(planned_df["Date"])
    planned_df = planned_df.set_index("Date")

    # Handle actual progress data
    if "Date" not in act_df.columns:
        # No actual progress provided
        return _create_progress_dataframe_without_actual(planned_df, timeline)

    # Parse actual dates and progress
    act_df["Date"] = pd.to_datetime(act_df["Date"], errors="coerce")
    act_df = act_df.dropna(subset=["Date"])
    
    if act_df.empty:
        return _create_progress_dataframe_without_actual(planned_df, timeline)

    # Extract progress data
    act_df["Progress"] = _extract_progress_values(act_df)
    
    # Aggregate actual progress by date
    actual_daily = act_df.groupby(act_df["Date"].dt.normalize()).agg({"Progress": "mean"})
    actual_daily.index.name = "Date"

    # Combine planned and actual data
    return _combine_progress_data(planned_df, actual_daily, timeline)


def _create_progress_dataframe_without_actual(planned_df: pd.DataFrame, timeline: pd.DatetimeIndex) -> pd.DataFrame:
    """Create progress DataFrame when no actual data is available."""
    result_df = planned_df.reset_index()
    result_df["Progress"] = 0.0
    result_df["CumulativeActual"] = result_df["Progress"].cumsum().clip(upper=1.0)
    result_df["ProgressDeviation"] = result_df["CumulativeActual"] - result_df["PlannedProgress"]
    return result_df


def _extract_progress_values(act_df: pd.DataFrame) -> pd.Series:
    """Extract progress values from actual DataFrame with fallback handling."""
    if "Progress" in act_df.columns:
        return pd.to_numeric(act_df["Progress"], errors="coerce").fillna(0.0)
    
    # Try alternative column names
    progress_aliases = ["Pct", "Percentage", "Percent", "Value", "Progress%"]
    for alias in progress_aliases:
        if alias in act_df.columns:
            return pd.to_numeric(act_df[alias], errors="coerce").fillna(0.0)
    
    # Default to zero progress
    return pd.Series([0.0] * len(act_df), index=act_df.index)


def _combine_progress_data(planned_df: pd.DataFrame, actual_daily: pd.DataFrame, 
                          timeline: pd.DatetimeIndex) -> pd.DataFrame:
    """Combine planned and actual progress data."""
    full_index = pd.DatetimeIndex(timeline)
    
    # Reindex actual data to full timeline
    actual_daily = actual_daily.reindex(full_index)
    actual_daily["Progress"] = actual_daily["Progress"].fillna(0.0)
    
    # Calculate cumulative actual progress
    actual_daily["CumulativeActual"] = actual_daily["Progress"].cumsum().clip(upper=1.0)

    # Combine datasets
    combined = pd.DataFrame(index=full_index)
    combined["PlannedProgress"] = planned_df["PlannedProgress"].reindex(full_index, fill_value=0.0)
    combined["Progress"] = actual_daily["Progress"]
    combined["CumulativeActual"] = actual_daily["CumulativeActual"]
    combined["ProgressDeviation"] = combined["CumulativeActual"] - combined["PlannedProgress"]
    
    return combined.reset_index().rename(columns={"index": "Date"})
