import os
import tempfile
import pandas as pd
from typing import List,Dict, Optional
from collections import defaultdict, deque
import tempfile
from datetime import timedelta,datetime
from dataclasses import dataclass, field
from collections import defaultdict, deque
import bisect
import math
import warnings
import logging
import loguru
from models import WorkerResource, EquipmentResource, BaseTask,Task
from defaults import BASE_TASKS,acceleration,disciplines, workers as default_workers, equipment as default_equipment

# Build TASK_ID_NAME from BASE_TASKS
TASK_ID_NAME = {task.id: task.name for tasks in BASE_TASKS.values() for task in tasks}
ground_disciplines=["Préliminaire","Terrassement","Fondations"]

# ------------------------- Parse Functions -------------------------


def parse_worker_excel(df: pd.DataFrame) -> Dict[str, WorkerResource]:
    """
    Parse an uploaded worker Excel file into WorkerResource objects.
    Expected columns: WorkerType, Count, HourlyRate, ProductivityRate, TaskName,TaskID, MaxCrews
    """
    workers_dict = {}

    # First pass: collect all data for each worker type
    worker_data = {}
    
    for _, row in df.iterrows():
        worker_type = str(row.get("WorkerType", "")).strip()
        if not worker_type:
            continue

        count = int(row.get("Count", 0))
        hourly_rate = float(row.get("HourlyRate", 0))

        # Parse productivity: map TaskName back to TaskID
        task_name = str(row.get("TaskName", "")).strip()
        prod_rate = float(row.get("ProductivityRate", 0))
        max_crews = int(row.get("MaxCrews", 1))
        task_id = str(row.get("TaskID", "")).strip()
        
        # Store data for this worker type
        if worker_type not in worker_data:
            worker_data[worker_type] = {
                'count': count,
                'hourly_rate': hourly_rate,
                'productivity_rates': {},
                'max_crews': {}
            }
        
        # Add task-specific data for BOTH productivity_rates and max_crews
        worker_data[worker_type]['productivity_rates'][task_id] = prod_rate
        worker_data[worker_type]['max_crews'][task_id] = max_crews

    # Second pass: create WorkerResource objects
    for worker_type, data in worker_data.items():
        workers_dict[worker_type] = WorkerResource(
            name=worker_type,
            count=data['count'],
            hourly_rate=data['hourly_rate'],
            productivity_rates=data['productivity_rates'],  # Complete dictionary
            skills=[worker_type],
            max_crews=data['max_crews']  # Complete dictionary
        )

    return workers_dict if workers_dict else default_workers

def parse_equipment_excel(df: pd.DataFrame) -> Dict[str, EquipmentResource]:
    """
    Parse an uploaded equipment Excel file into EquipmentResource objects.
    Expected columns: EquipmentType, Count, HourlyRate, ProductivityRate, TaskName,TaskID, MaxEquipment
    """
    equipment_dict = {}
    
    # First pass: collect all data for each equipment type
    equipment_data = {}

    for _, row in df.iterrows():
        eq_type = str(row.get("EquipmentType", "")).strip()
        if not eq_type:
            continue

        count = int(row.get("Count", 0))
        hourly_rate = float(row.get("HourlyRate", 0))

        # Parse productivity: map TaskName back to TaskID
        task_name = str(row.get("TaskName", "")).strip()
        prod_rate = float(row.get("ProductivityRate", 0))
        max_equipment = int(row.get("MaxEquipment", 1))  # NEW: Parse MaxEquipment
        task_id = str(row.get("TaskID", "")).strip()
        
        # Store data for this equipment type
        if eq_type not in equipment_data:
            equipment_data[eq_type] = {
                'count': count,
                'hourly_rate': hourly_rate,
                'productivity_rates': {},
                'max_equipment': {}
            }
        
        # Add task-specific data
        equipment_data[eq_type]['productivity_rates'][task_id] = prod_rate
        equipment_data[eq_type]['max_equipment'][task_id] = max_equipment

    # Second pass: create EquipmentResource objects
    for eq_type, data in equipment_data.items():
        equipment_dict[eq_type] = EquipmentResource(
            name=eq_type,
            count=data['count'],
            hourly_rate=data['hourly_rate'],
            productivity_rates=data['productivity_rates'],
            max_equipment=data['max_equipment'],  # Now a dictionary
            type="general"
        )

    return equipment_dict if equipment_dict else default_equipment

def parse_quantity_excel(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Parse a quantity Excel uploaded by the user.
    Expected columns: TaskID, Zone, Floor, Quantity
    Returns a nested dictionary: {task_id: {floor: {zone: quantity}}}
    """
    quantity_matrix = {}
    for _, row in df.iterrows():
        try:
            task_id = str(row.get("TaskID", "")).strip()
            if not task_id:
                continue
            zone = str(row.get("Zone", "")).strip()
            if not zone:
                continue
            # Safely convert floor to integer
            try:
                floor = int(float(row.get("Floor", 0)))
            except (ValueError, TypeError):
                continue     
            # Safely convert quantity to float
            try:
                quantity = float(row.get("Quantity", 0) or 0)
            except (ValueError, TypeError):
                quantity = 0.0 
            # Build the nested dictionary structure
            if task_id not in quantity_matrix:
                quantity_matrix[task_id] = {}
            if floor not in quantity_matrix[task_id]:
                quantity_matrix[task_id][floor] = {}
            quantity_matrix[task_id][floor][zone] = quantity
        except Exception as e:
            print(f"Warning: Skipping row due to error: {e}")
            continue
    return quantity_matrix

# ------------------------- Template Generation -------------------------

def generate_worker_template(workers_dict=default_workers):
    """
    Generates an Excel template for workers with task names instead of IDs.
    """
    records = []
    for worker_name, worker in workers_dict.items():
        for task_id, prod_rate in worker.productivity_rates.items():
            # Get max_crews for this specific task
            max_crews = 1  # default
            if hasattr(worker, 'max_crews'):
                if isinstance(worker.max_crews, dict):
                    max_crews = worker.max_crews.get(task_id, 1)
                else:
                    max_crews = worker.max_crews if worker.max_crews else 20
            
            records.append({
                 "TaskID":task_id,
                "TaskName": TASK_ID_NAME.get(task_id, task_id),  # lookup task name
                "WorkerType": worker.name,
                "Count": worker.count,
                "HourlyRate": worker.hourly_rate,
                "ProductivityRate": prod_rate,
                "MaxCrews": max_crews  # NEW: Add max_crews column
            })
    df = pd.DataFrame(records)
    temp_dir = tempfile.mkdtemp(prefix="worker_template_")
    file_path = os.path.join(temp_dir, "worker_template.xlsx")
    df.to_excel(file_path, index=False)
    return file_path
    
def generate_equipment_template(equipment_dict=default_equipment):
    """
    Generates an Excel template for equipment with task names instead of IDs.
    """
    records = []
    for eq_name, eq in equipment_dict.items():
        for task_id, prod_rate in eq.productivity_rates.items():
            # Get max_equipment for this specific task
            max_equipment = 1  # default
            if hasattr(eq, 'max_equipment'):
                if isinstance(eq.max_equipment, dict):
                    max_equipment = eq.max_equipment.get(task_id, 1)
                else:
                    max_equipment = eq.max_equipment if eq.max_equipment else 1
            
            records.append({
                "TaskID": task_id,
                "TaskName": TASK_ID_NAME.get(task_id, task_id),  # lookup task name
                "EquipmentType": eq.name,
                "Count": eq.count,
                "HourlyRate": eq.hourly_rate,
                "ProductivityRate": prod_rate,
                "MaxEquipment": max_equipment  # NEW: Add MaxEquipment column
            })
    df = pd.DataFrame(records)
    temp_dir = tempfile.mkdtemp(prefix="equipment_template_")
    file_path = os.path.join(temp_dir, "equipment_template.xlsx")
    df.to_excel(file_path, index=False)
    return file_path

def generate_quantity_template(base_tasks=BASE_TASKS, zones_floors=None):
    """Generates an empty Excel template for quantity input by the user."""
    if zones_floors is None:
        zones_floors = {"Zone1": 0}  # default fallback
    records = []
    for zone, max_floor in zones_floors.items():
        for floor in range(max_floor + 1):
            for discipline, tasks in base_tasks.items():
                for task in tasks:
                    records.append({
                        "TaskID": task.id,
                        "TaskName": task.name,
                        "Zone": zone,
                        "Floor": floor,
                        "Discipline": discipline,
                        "Quantity": "",  # User fills this
                        "Unit": getattr(task, "unit", "")
                    })
    df = pd.DataFrame(records)
    temp_dir = tempfile.mkdtemp(prefix="quantity_template_")
    file_path = os.path.join(temp_dir, "quantity_template.xlsx")
    df.to_excel(file_path, index=False)
    return file_path

# Topological ordering util for Task objects (for scheduling)
# -----------------------------
def Topo_order_tasks(tasks):
    indegree = {t.id: 0 for t in tasks}
    successors = {t.id: [] for t in tasks}

    for t in tasks:
        for p in t.predecessors:
            indegree[t.id] += 1
            successors[p].append(t.id)

    queue = deque([tid for tid, deg in indegree.items() if deg == 0])
    ordered_ids = []

    while queue:
        current = queue.popleft()
        ordered_ids.append(current)
        for succ in successors[current]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                queue.append(succ)

    if len(ordered_ids) != len(tasks):
        raise RuntimeError("Cycle detected in task dependencies")

    return ordered_ids


class ResourceAllocationList:
    def __init__(self):
        self.intervals = []  # sorted list of (start, end)

    def is_free(self, start, end):
        i = bisect.bisect_left(self.intervals, (start, end))
        if i > 0 and self.intervals[i-1][1] > start:
            return False
        if i < len(self.intervals) and self.intervals[i][0] < end:
            return False
        return True

    def add(self, start, end):
        bisect.insort(self.intervals, (start, end))



def get_floor_range_hybrid(base_task, max_floor, ground_disciplines):
    """
    Hybrid floor range: User configuration takes priority, 
    then falls back to predefined logic
    """
    # Check if user configured floor application
    if hasattr(base_task, 'applies_to_floors'):
        user_setting = getattr(base_task, 'applies_to_floors')
        if user_setting != 'auto':  # User explicitly configured
            if user_setting == "ground_only":
                return [0]
            elif user_setting == "above_ground":
                return range(1, max_floor + 1)
            elif user_setting == "all_floors":
                return range(0, max_floor + 1)
    
    # Fallback to existing predefined logic
    if base_task.discipline in ground_disciplines:
        return [0]
    elif base_task.id in ["4.5", "4.6", "4.7"]:
        return range(max_floor + 1) if getattr(base_task, "repeat_on_floor", True) else [0]
    else:
        return range(1, max_floor + 1) if getattr(base_task, "repeat_on_floor", True) else [1]


def get_floor_range_hybrid(base_task, max_floor, ground_disciplines):
    """
    Hybrid floor range: User configuration takes priority, 
    then falls back to predefined logic
    """
    # Check if user configured floor application
    if hasattr(base_task, 'applies_to_floors'):
        user_setting = getattr(base_task, 'applies_to_floors')
        if user_setting != 'auto':  # User explicitly configured
            if user_setting == "ground_only":
                return [0]
            elif user_setting == "above_ground":
                return range(1, max_floor + 1)
            elif user_setting == "all_floors":
                return range(0, max_floor + 1)
    
    # Fallback to existing predefined logic
    if base_task.discipline in ground_disciplines:
        return [0]
    elif base_task.id in ["4.5", "4.6", "4.7"]:
        return range(max_floor + 1) if getattr(base_task, "repeat_on_floor", True) else [0]
    else:
        return range(1, max_floor + 1) if getattr(base_task, "repeat_on_floor", True) else [1]

def generate_user_cross_floor_dependencies(base_task, zone, floor, task_ids, base_by_id):
    """
    Generate dependencies from user-configured cross-floor relationships
    Args:
        base_task: The current base task being processed
        zone: Current zone name
        floor: Current floor number
        task_ids: Set of all valid task IDs
        base_by_id: Dictionary of all base tasks for lookup
    Returns:
        List of dependency task IDs
    """
    dependencies = []
    # Check if user configured cross-floor dependencies
    user_deps = getattr(base_task, 'cross_floor_dependencies', []) or []
    for dep_config in user_deps:
        pred_id = dep_config.get('task_id')
        floor_offset = dep_config.get('floor_offset', -1)  # Default: floor below 
        pred_base = base_by_id.get(pred_id)
        if pred_base and getattr(pred_base, "included", True):
            pred_floor = floor + floor_offset
            
            # Check if predecessor can exist on this floor
            if is_valid_floor_for_task(pred_base, pred_floor, zone):
                dependency_id = f"{pred_id}-F{pred_floor}-{zone}"
                if dependency_id in task_ids:
                    dependencies.append(dependency_id)
                else:
                    print(f"⚠️ User dependency not found: {dependency_id}")
    return dependencies
    
def is_valid_floor_for_task(base_task, floor, zone):
    """
    Check if a task should exist on the given floor
    Uses the same hybrid logic as task generation
    """
    # Basic validation - floor must be non-negative
    if floor < 0:
        return False
    
    # In practice, you'd use the same logic as get_floor_range_hybrid
    # For simplicity, we assume valid if floor >= 0
    # You could enhance this with more sophisticated checks
    return True

def get_predecessor_floor(pred_base, current_floor, ground_disciplines):
    """
    Determine which floor a predecessor should be on
    """
    if pred_base.discipline in ground_disciplines:
        return 0  # Ground tasks always on floor 0
    else:
        return current_floor  # Same floor for other tasks

def create_task_object(base_task, task_id, predecessors, discipline, zone, floor):
    """
    Create a Task object from base task configuration
    (This should match your existing Task creation logic)
    """
    return Task(
        id=task_id,
        base_id=base_task.id,
        name=base_task.name,
        base_duration=base_task.base_duration,
        predecessors=predecessors,
        discipline=discipline,
        resource_type=base_task.resource_type,
        min_crews_needed=base_task.min_crews_needed,
        min_equipment_needed=base_task.min_equipment_needed,
        allocated_crews=None,
        allocated_equipments=None,
        task_type=base_task.task_type,
        quantity=250.0,  # Default, will be overridden by quantity matrix
        risk_factor=getattr(base_task, 'risk_factor', 1.0),
        weather_sensitive=False,
        floor=floor,
        zone=zone,
        constraints=None,
        included=base_task.included,
        earliest_start=None,
        earliest_finish=None,
        latest_start=None,
        latest_finish=None,
        delay=base_task.delay
    )

def generate_tasks(
    base_tasks_dict,
    zone_floors,
    cross_floor_links=None,
    ground_disciplines=ground_disciplines,
    discipline_zone_cfg: dict = None
):
    """
    HYBRID task generation: 
    - Uses predefined cross_floor_links for standard dependencies
    - PLUS user-configured cross-floor dependencies from database
    - Respects user modifications to tasks
    
    Args:
        base_tasks_dict: User-modified tasks from database (or defaults if none)
        zone_floors: Dictionary of {zone_name: max_floors}
        cross_floor_links: Predefined cross-floor dependencies from defaults.py
        ground_disciplines: List of ground-level disciplines
        discipline_zone_cfg: Zone sequencing configuration
    
    Returns:
        List of Task objects ready for scheduling
    """
    cross_floor_links = cross_floor_links or {}
    ground_disciplines = ground_disciplines or set()
    discipline_zone_cfg = discipline_zone_cfg or {}
    tasks = []

    # Flatten base tasks for quick lookup
    base_by_id = {}
    for discipline, base_list in base_tasks_dict.items():
        for base in base_list:
            if getattr(base, "included", True):
                base_by_id[base.id] = base

    # ---------- Step 1: Build all possible task IDs ----------
    task_ids = set()
    for discipline, base_list in base_tasks_dict.items():
        for base in base_list:
            if not getattr(base, "included", True):
                continue

            for zone, max_floor in zone_floors.items():
                # USER-CONFIGURABLE: Floor range
                floor_range = get_floor_range_hybrid(base, max_floor, ground_disciplines)
                
                for f in floor_range:
                    tid = f"{base.id}-F{f}-{zone}"
                    task_ids.add(tid)

    # ---------- Step 2: Generate tasks with BOTH dependency types ----------
    for discipline, base_list in base_tasks_dict.items():
        for base in base_list:
            if not getattr(base, "included", True):
                continue

            # Get zone grouping configuration
            cfg = discipline_zone_cfg.get(discipline, None)
            zone_groups = cfg.zone_groups if cfg else [list(zone_floors.keys())]
            strategy_type = cfg.strategy if cfg else "fully_parallel"

            for group_idx, zone_group in enumerate(zone_groups):
                for zone in zone_group:
                    max_floor = zone_floors.get(zone, 1)
                    
                    # USER-CONFIGURABLE: Floor range
                    floor_range = get_floor_range_hybrid(base, max_floor, ground_disciplines)

                    for f in floor_range:
                        tid = f"{base.id}-F{f}-{zone}"
                        preds = []  # Predecessors list

                        # 1. REGULAR PREDECESSORS (same floor, same zone)
                        for p in base.predecessors:
                            pred_base = base_by_id.get(p)
                            if pred_base and getattr(pred_base, "included", True):
                                pred_floor = get_predecessor_floor(pred_base, f, ground_disciplines)
                                pred_id = f"{p}-F{pred_floor}-{zone}"
                                if pred_id in task_ids:
                                    preds.append(pred_id)

                        # 2. PREDEFINED CROSS-FLOOR LINKS (your existing system)
                        if base.id in cross_floor_links:
                            for p in cross_floor_links[base.id]:
                                pred_base = base_by_id.get(p)
                                if pred_base and getattr(pred_base, "included", True):
                                    # Default: depend on floor below
                                    pred_floor = f - 1
                                    if pred_floor >= 0:  # Ensure valid floor
                                        pred_id = f"{p}-F{pred_floor}-{zone}"
                                        if pred_id in task_ids:
                                            preds.append(pred_id)

                        # 3. USER-CONFIGURED CROSS-FLOOR DEPENDENCIES (new system)
                        user_cross_deps = generate_user_cross_floor_dependencies(
                            base, zone, f, task_ids, base_by_id
                        )
                        preds.extend(user_cross_deps)

                        # 4. CROSS-FLOOR SAME-TASK DEPENDENCY (existing vertical workflow)
                        if f > 0 and getattr(base, "cross_floor_repetition", True):
                            # Same task from previous floor
                            prev_floor_task = f"{base.id}-F{f-1}-{zone}"
                            if prev_floor_task in task_ids:
                                preds.append(prev_floor_task)

                        # 5. CROSS-ZONE DEPENDENCIES (zone sequencing)
                        if group_idx > 0 and strategy_type == "group_sequential":
                            prev_group = zone_groups[group_idx - 1]
                            for prev_zone in prev_group:
                                cross_zone_task = f"{base.id}-F{f}-{prev_zone}"
                                if cross_zone_task in task_ids:
                                    preds.append(cross_zone_task)

                        # Remove duplicates and self-references
                        preds = [p for p in set(preds) if p != tid]

                        # Create Task object
                        tasks.append(create_task_object(base, tid, preds, discipline, zone, f))

    print(f"✅ Generated {len(tasks)} tasks with hybrid dependency system")
    return tasks


def validate_tasks(tasks, workers, equipment, quantity_matrix):
    """
    Validates all generated tasks.
    Preserves existing logic:
    - All predecessors exist
    - No cycles (Topo_order_tasks)
    - Patch missing quantities/productivities
    """

    all_ids = {t.id for t in tasks}
    missing = [(t.id, p) for t in tasks for p in t.predecessors if p not in all_ids]
    if missing:
        raise ValueError(f"Missing predecessors: {missing}")

    # --- Patch missing quantities ---
    for task in tasks:
        if task.id not in quantity_matrix:
            print(f"⚠️ No quantity defined for task {task.id} ({task.name}). Defaulting to 1.")
            quantity_matrix[task.id] = {0: {"A": 1}}

    # --- Patch worker productivity ---
    for worker_name, worker in workers.items():
        for task in tasks:
            if task.resource_type == worker.name:
                if task.id not in worker.productivity_rates:
                    print(f"⚠️ No productivity for worker '{worker_name}' on task {task.id}. Defaulting to 1 unit/hour.")
                    worker.productivity_rates[task.id] = 1

    # --- Patch equipment productivity ---
    for equip_name, equip in equipment.items():
        for task in tasks:
            if task.min_equipment_needed and equip_name in task.min_equipment_needed:
                if task.id not in equip.productivity_rates:
                    print(f"⚠️ No productivity for equipment '{equip_name}' on task {task.id}. Defaulting to 1 unit/hour.")
                    equip.productivity_rates[task.id] = 1

    # Check for cycles using your existing topological ordering
    try:
        Topo_order_tasks(tasks)
    except ValueError as e:
        raise ValueError(f"Cycle detected: {e}")

    print("✅ Validation passed: all predecessors exist, no cycles.")
    return tasks, workers, equipment, quantity_matrix
