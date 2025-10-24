# ==== Standard Library ====
from collections import deque
from typing import List, Dict, Tuple, Optional, Set
import logging
import pandas as pd

from models import Task,BaseTask, WorkerResource, EquipmentResource  # Data models representing entities

from utils.resources import AdvancedResourceManager, EquipmentResourceManager
from utils.calendar import AdvancedCalendar
from utils.duration import DurationCalculator



class AdvancedScheduler:
    """
    Advanced construction scheduler with resource constraints and optimization.
    """
    
    def __init__(self, tasks: List[Task], workers: Dict[str, WorkerResource],
                 equipment: Dict[str, EquipmentResource], calendar: AdvancedCalendar,
                 duration_calc: DurationCalculator):
        """
        Initialize scheduler with tasks and resources.
        
        Args:
            tasks: List of tasks to schedule
            workers: Worker resources
            equipment: Equipment resources  
            calendar: Calendar for date calculations
            duration_calc: Duration calculator
        """
        self.tasks = [t for t in tasks if getattr(t, "included", True)]
        self.task_map = {t.id: t for t in self.tasks}
        self.workers = workers
        self.equipment = equipment
        self.calendar = calendar
        self.duration_calc = duration_calc
        self.worker_manager = AdvancedResourceManager(workers)
        self.equipment_manager = EquipmentResourceManager(equipment)

    def _all_predecessors_scheduled(self, task: Task, schedule: Dict) -> bool:
        """Check if all predecessors are scheduled."""
        for predecessor in task.predecessors:
            if predecessor not in self.task_map:
                raise ValueError(f"Task {task.id} has predecessor {predecessor} not in task set")
            if predecessor not in schedule:
                return False
        return True

    def _earliest_start_from_predecessors(self, task: Task, schedule: Dict) -> pd.Timestamp:
        """Calculate earliest start date based on predecessors."""
        pred_end_dates = [
            self.calendar.add_calendar_days(schedule[p][1], self.task_map[p].delay)
            for p in task.predecessors
            if p in schedule and schedule[p][1] is not None
        ]
        
        if not pred_end_dates:
            logger.debug(f"Task {task.id}: No scheduled predecessors found")
            return self.calendar.current_date
            
        return max(pred_end_dates)

    def _allocate_resources_for_window(self, task: Task, start_date: pd.Timestamp, 
                                     duration_days: int) -> Tuple[Optional[int], Dict, pd.Timestamp]:
        """
        Allocate resources for a specific time window without committing.
        
        Returns:
            Tuple of (crews, equipment, end_date)
        """
        end_date = self.calendar.add_workdays(start_date, duration_days)
        
        # Calculate possible allocations
        possible_crews = None
        if task.task_type in ("worker", "hybrid"):
            possible_crews = self.worker_manager.compute_allocation(task, start_date, end_date)

        possible_equip = {}
        if task.task_type in ("equipment", "hybrid") and (task.min_equipment_needed or {}):
            possible_equip = self.equipment_manager.compute_allocation(task, start_date, end_date) or {}

        return possible_crews, possible_equip, end_date

    def _check_feasibility(self, task: Task, possible_crews: Optional[int], 
                          possible_equip: Dict) -> Tuple[bool, bool]:
        """Check if allocated resources meet minimum requirements."""
        min_crews = getattr(task, "min_crews_needed", max(1, task.min_crews_needed))
        
        # Check worker feasibility
        feasible_workers = True
        if task.task_type in ("worker", "hybrid"):
            feasible_workers = (possible_crews is not None and possible_crews >= min_crews)

        # Check equipment feasibility
        feasible_equip = True
        if task.task_type in ("equipment", "hybrid") and (task.min_equipment_needed or {}):
            for eq_key, min_req in task.min_equipment_needed.items():
                eq_choices = eq_key if isinstance(eq_key, (tuple, list)) else (eq_key,)
                allocated_total = sum(possible_equip.get(eq, 0) for eq in eq_choices)
                if allocated_total < min_req:
                    feasible_equip = False
                    break

        return feasible_workers, feasible_equip

    def _schedule_instantaneous_task(self, task: Task, schedule: Dict, ready: deque, 
                                   pred_count: Dict, unscheduled: Set):
        """Schedule a task with zero duration."""
        start_date = self._earliest_start_from_predecessors(task, schedule)
        schedule[task.id] = (start_date, start_date)
        unscheduled.remove(task.id)
        task.allocated_crews = 0
        task.allocated_equipments = {}
        
        # Update successors
        for successor in [s for s in self.task_map if task.id in self.task_map[s].predecessors]:
            pred_count[successor] -= 1
            if pred_count[successor] == 0:
                ready.append(successor)

    def _allocate_and_schedule_task(self, task: Task, start_date: pd.Timestamp, 
                                  schedule: Dict) -> Tuple[pd.Timestamp, pd.Timestamp, int, Dict]:
        """
        Allocate resources and schedule a task.
        
        Returns:
            Tuple of (start_date, end_date, crews, equipment)
        """
        duration_days = self.duration_calc.calculate_duration(task)
        
        if not isinstance(duration_days, int) or duration_days < 0:
            raise ValueError(f"Invalid duration for {task.id}: {duration_days}")

        # Resource allocation loop
        allocated_crews = None
        allocated_equipments = None
        forward_attempts = 0

        while forward_attempts < MAX_FORWARD_ATTEMPTS:
            # Get resource allocations
            possible_crews, possible_equip, end_date = self._allocate_resources_for_window(
                task, start_date, duration_days
            )

            # Check feasibility
            feasible_workers, feasible_equip = self._check_feasibility(
                task, possible_crews, possible_equip
            )

            if feasible_workers and feasible_equip:
                # Calculate duration with actual allocations
                actual_duration = self.duration_calc.calculate_duration(
                    task,
                    allocated_crews=possible_crews,
                    allocated_equipments=possible_equip
                )
                
                # Re-check with actual duration
                final_crews, final_equip, final_end = self._allocate_resources_for_window(
                    task, start_date, actual_duration
                )
                
                final_feasible_workers, final_feasible_equip = self._check_feasibility(
                    task, final_crews, final_equip
                )
                
                if final_feasible_workers and final_feasible_equip:
                    # Release previous allocations and commit new ones
                    self.worker_manager.release(task.id)
                    self.equipment_manager.release(task.id)
                    
                    allocated_crews = final_crews
                    allocated_equipments = final_equip

                    if allocated_crews:
                        self.worker_manager.allocate(task, start_date, final_end, allocated_crews)
                    if allocated_equipments:
                        self.equipment_manager.allocate(task, start_date, final_end, allocated_equipments)

                    duration_days = actual_duration
                    end_date = final_end
                    break

            # Move to next workday
            start_date = self.calendar.add_workdays(start_date, 1)
            forward_attempts += 1

        if forward_attempts >= MAX_FORWARD_ATTEMPTS:
            raise RuntimeError(
                f"Could not find resource window for task {task.id} ({task.name}) "
                f"after {MAX_FORWARD_ATTEMPTS} attempts. Required: {task.min_crews_needed} crews, "
                f"Equipment: {task.min_equipment_needed}"
            )

        return start_date, end_date, allocated_crews, allocated_equipments

    def generate(self) -> Dict[str, Tuple[pd.Timestamp, pd.Timestamp]]:
        """
        Generate optimized schedule with resource constraints.
        
        Returns:
            Dictionary mapping task IDs to (start_date, end_date) tuples
        """
        schedule = {}
        unscheduled = set(self.task_map.keys())

        # Initialize predecessor counts and ready queue
        pred_count = {tid: len(self.task_map[tid].predecessors) for tid in self.task_map}
        ready = deque([tid for tid, cnt in pred_count.items() if cnt == 0])

        # Validate task references early
        for tid, task in self.task_map.items():
            for predecessor in task.predecessors:
                if predecessor not in self.task_map:
                    raise ValueError(f"Task {tid} references non-existent predecessor {predecessor}")

        # Precompute nominal durations
        for tid, task in self.task_map.items():
            try:
                nominal_duration = self.duration_calc.calculate_duration(task)
                if not isinstance(nominal_duration, int) or nominal_duration < 0:
                    raise ValueError(f"Invalid nominal duration {nominal_duration!r}")
                task.nominal_duration = nominal_duration
            except Exception as e:
                logger.error(f"Task {tid}: cannot compute nominal duration => {e!r}")
                raise

        # Main scheduling loop
        attempts = 0
        while unscheduled:
            if not ready:
                pending_tasks = ", ".join(sorted(unscheduled))
                raise RuntimeError(f"No tasks ready but unscheduled remain: {pending_tasks}")

            tid = ready.popleft()
            task = self.task_map[tid]

            # Check if all predecessors are scheduled
            if not self._all_predecessors_scheduled(task, schedule):
                ready.append(tid)
                attempts += 1
                if attempts > MAX_SCHEDULING_ATTEMPTS:
                    raise RuntimeError("Scheduler stuck waiting for predecessors.")
                continue

            # Reset attempts counter on successful processing
            attempts = 0
            
            # Get earliest start date
            start_date = self._earliest_start_from_predecessors(task, schedule)
            task.earliest_start = start_date

            # Handle instantaneous tasks
            if task.nominal_duration == 0:
                self._schedule_instantaneous_task(task, schedule, ready, pred_count, unscheduled)
                continue

            # Allocate resources and schedule task
            start_date, end_date, crews, equipment = self._allocate_and_schedule_task(
                task, start_date, schedule
            )

            # Final dependency validation
            for predecessor in task.predecessors:
                pred_end = schedule[predecessor][1]
                if start_date < pred_end:
                    raise RuntimeError(
                        f"Dependency violation: Task {task.id} starts {start_date} "
                        f"before predecessor {predecessor} ends {pred_end}"
                    )

            # Record schedule
            schedule[task.id] = (start_date, end_date)
            unscheduled.remove(task.id)
            task.allocated_crews = crews
            task.allocated_equipments = equipment
            
            # Update successor readiness
            for successor in [s for s in self.task_map if task.id in self.task_map[s].predecessors]:
                pred_count[successor] -= 1
                if pred_count[successor] == 0:
                    ready.append(successor)

        logger.info(f"✅ Schedule generated successfully for {len(schedule)} tasks")
        return schedule
