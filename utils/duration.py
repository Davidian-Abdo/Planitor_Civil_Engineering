from collections import deque
from typing import List, Dict, Tuple, Optional, Set
import logging
import pandas as pd
from models import WorkerResource, EquipmentResource

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
