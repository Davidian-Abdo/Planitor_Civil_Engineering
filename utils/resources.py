





class AdvancedResourceManager:
    """
    Manages worker crews with flexible allocation:
      - If full crews available -> allocate full crews_needed (after acceleration/clamps)
      - If not, allocate the maximum possible >= min_crews_needed
      - If less than min_crews_needed -> allocation fails (returns 0)
    Allocations stored as: allocations[res_name] -> list of (task_id, resource_name, units, start, end)
    """

    def __init__(self, workers: Dict[str, WorkerResource]):
        self.workers = workers
        self.allocations = defaultdict(list)

    def _used_crews(self, res_name, start, end):
        """Sum units already reserved overlapping [start, end)"""
        used = 0
        for (_tid, _rname, units, s, e) in self.allocations[res_name]:
            # overlap if not (end <= s or start >= e)
            if not (end <= s or start >= e):
                used += units
        return used

    def compute_allocation(self, task, start, end):
        """
        Flexible allocation policy.
        Returns integer number of crews to allocate (>= min_crews_needed), or 0 if cannot satisfy minimum.
        """
        if task.task_type == "equipment":
            return 0  # worker manager not responsible

        res_name = task.resource_type
        if res_name not in self.workers:
            return 0

        res = self.workers[res_name]
        total_pool = int(res.count)

        # find already-used crews in the window
        used = self._used_crews(res_name, start, end)
        available = max(0, total_pool - used)

        min_needed = max(1, int(task.min_crews_needed))

        # acceleration config may increase desired crews (factor) but we cap by task max and pool limits
        acc = acceleration.get(
            task.discipline,
            acceleration.get("default", {"factor": 1.0})
        )
        factor = acc.get("factor", 1.0)

        # ideal after acceleration (but must be <= disc_max and <= per-res max)
        candidate = int(math.ceil(min_needed * factor))
        
        # FIXED: Handle max_crews properly for both dict and legacy int types
        res_max_value = getattr(res, "max_crews", None)
        if res_max_value is None:
           res_max_value=25 
        
        if isinstance(res_max_value, dict):
            # Dictionary case: get task-specific limit
            task_id = getattr(task, 'id', None)
            if task_id and task_id in res_max_value:
                task_max = res_max_value[task_id]
                candidate = min(candidate, int(task_max))
                print(f"[ALLOC DEBUG] Using task-specific max_crews: {task_max} for task {task_id}")
        elif res_max_value is not None :
            if res_max_value > 0:
            # Legacy single integer case
                candidate = min(candidate, int(res_max_value))
        
        print(f"[ALLOC DEBUG] {task.id} disc={task.discipline} min_needed={min_needed} "
              f"factor={factor} candidate={candidate} pool={total_pool} used={used}")
        
        # final allocation is the maximum we can give within [min_needed, candidate] limited by available
        allocated = min(candidate, available)

        # If allocated is less than minimum, fail
        if allocated < min_needed:
            print(f"[ALLOC FAIL] {task.id} pool={total_pool} used={used} available={available} min_needed={min_needed} candidate={candidate}")
            return 0

        return int(allocated)

    def can_allocate(self, task, start, end):
        alloc = self.compute_allocation(task, start, end)
        return alloc >= max(1, getattr(task, "min_crews_needed", max(1, task.crews_needed)))

    def allocate(self, task, start, end, units):
        """
        Reserve exactly `units` crews for this task in [start, end).
        Returns units reserved or 0 on failure.
        """
        if units is None or units <= 0:
            return 0
        # append allocation record
        self.allocations[task.resource_type].append((task.id, task.resource_type, int(units), start, end))
        return int(units)

    def release(self, task_id):
        """Release all allocations associated with a task id."""
        for res_name in list(self.allocations.keys()):
            self.allocations[res_name] = [a for a in self.allocations[res_name] if a[0] != task_id]
# -----------------------------
# Equipment Manager (shared use)
# -----------------------------

class EquipmentResourceManager:
    """
    Professional equipment allocation manager.

    Features:
    - Split allocation across alternative equipment types
    - Respect individual equipment maximums (max_equipment)
    - Multi-phase allocation: min_required → accelerated_target
    - Cost-aware optimization with weighted strategy
    - Allocations stored as: allocations[equipment_name] -> list of (task_id, equipment_name, units, start, end)
    """

    def __init__(self, equipment: dict):
        self.equipment = equipment
        self.allocations = defaultdict(list)

    def allocate(self, task, start, end, allocation: dict = None):
        """
        Reserve the explicit allocation dict {eq_name: units} for this task.
        If allocation is None, compute automatically.
        """
        if allocation is None:
            allocation = self.compute_allocation(task, start, end)
        if not allocation:
            return None
        for eq_name, units in allocation.items():
            self.allocations[eq_name].append((task.id, eq_name, int(units), start, end))
        return allocation

    def _used_units(self, eq_name, start, end):
        """Sum units already reserved overlapping [start, end)."""
        used = 0
        for (_tid, _, units, s, e) in self.allocations[eq_name]:
            if not (end <= s or start >= e):
                used += units
        return used

    def compute_allocation(self, task, start, end):
        """
        Advanced equipment allocation with professional multi-equipment support.

        Returns: {equipment_name: allocated_units} or None if requirements cannot be met
        """
        if not task.min_equipment_needed:
            return {}

        final_allocation = {}

        for eq_key, requested_units in task.min_equipment_needed.items():
            eq_choices = self._normalize_equipment_choices(eq_key)

            # Phase 1: Calculate requirements with acceleration
            min_required = int(requested_units)
            target_demand = self._calculate_accelerated_demand(min_required, task.discipline)

            # Phase 2: Analyze equipment availability
            equipment_analysis = self._analyze_equipment_availability(eq_choices, start, end, target_demand, task)
            if not equipment_analysis:
                self._log_allocation_failure(task, eq_choices, min_required, equipment_analysis)
                return None

            # Phase 3: Multi-stage allocation
            allocation_result = self._perform_multi_stage_allocation(equipment_analysis, min_required, target_demand)
            if not allocation_result:
                self._log_allocation_failure(task, eq_choices, min_required, equipment_analysis)
                return None

            for eq_name, units in allocation_result.items():
                final_allocation[eq_name] = units

        return final_allocation

    def can_allocate(self, task, start, end):
        alloc = self.compute_allocation(task, start, end)
        return alloc is not None

    def release(self, task_id):
        """Release all allocations associated with this task."""
        for eq_name in list(self.allocations.keys()):
            self.allocations[eq_name] = [a for a in self.allocations[eq_name] if a[0] != task_id]

    # ------------------------ Helper Methods ------------------------

    def _normalize_equipment_choices(self, eq_key):
        """Normalize equipment choices to list format."""
        if isinstance(eq_key, (tuple, list)):
            return list(eq_key)
        return [eq_key]

    def _calculate_accelerated_demand(self, min_required, discipline):
        """Calculate accelerated demand with safety limits."""
        acceleration_config = acceleration.get(
            discipline,
            acceleration.get("default", {"factor": 1.0, "max_multiplier": 3.0})
        )
        factor = acceleration_config.get("factor", 1.0)
        max_multiplier = acceleration_config.get("max_multiplier", 3.0)
        accelerated = int(math.ceil(min_required * factor))
        return min(accelerated, int(min_required * max_multiplier))

    def _analyze_equipment_availability(self, eq_choices, start, end, target_demand, task):
        """Analyze equipment availability and constraints for alternatives."""
        equipment_analysis = {}
        total_available = 0

        for eq_name in eq_choices:
            if eq_name not in self.equipment:
                continue

            eq_res = self.equipment[eq_name]
            total_count = int(eq_res.count)
            used_units = self._used_units(eq_name, start, end)
            available_units = max(0, total_count - used_units)
            
            # FIXED: Handle max_equipment as dictionary for task-specific limits
            max_equipment_value = getattr(eq_res, "max_equipment", total_count)
            if isinstance(max_equipment_value, dict):
                # Get task-specific limit
                task_id = getattr(task, 'id', None)
                if task_id and task_id in max_equipment_value:
                    max_per_task = max_equipment_value[task_id]
                else:
                    max_per_task = total_count  # Fallback
            else:
                max_per_task = max_equipment_value
            
            allocatable_units = min(available_units, max_per_task)

            equipment_analysis[eq_name] = {
                'total_count': total_count,
                'used_units': used_units,
                'available_units': available_units,
                'allocatable_units': allocatable_units,
                'max_per_task': max_per_task,
                'hourly_rate': getattr(eq_res, 'hourly_rate', 100),
                'efficiency': getattr(eq_res, 'efficiency', 1.0)
            }

            total_available += allocatable_units

        if total_available < min(1, target_demand):
            return None

        return equipment_analysis

    def _perform_multi_stage_allocation(self, equipment_analysis, min_required, target_demand):
        """Allocate equipment in two stages: minimum and accelerated demand."""
        allocation = {}
        # Stage 1: Ensure minimum
        min_allocation = self._allocate_equipment_set(equipment_analysis, min_required, optimization='min_cost')
        if not min_allocation or sum(min_allocation.values()) < min_required:
            return None

        # Stage 2: Try to meet accelerated demand
        remaining_capacity = self._calculate_remaining_capacity(equipment_analysis, min_allocation)
        additional_demand = target_demand - sum(min_allocation.values())

        if additional_demand > 0 and remaining_capacity > 0:
            additional_allocation = self._allocate_equipment_set(
                equipment_analysis, additional_demand,
                optimization='balanced', existing_allocation=min_allocation
            )
            if additional_allocation:
                for eq_name, units in additional_allocation.items():
                    min_allocation[eq_name] = min_allocation.get(eq_name, 0) + units

        return min_allocation

    def _allocate_equipment_set(self, equipment_analysis, demand, optimization='min_cost', existing_allocation=None):
        allocation = existing_allocation.copy() if existing_allocation else {}
        remaining_demand = demand
        available_eq = self._get_optimized_equipment_list(equipment_analysis, allocation, optimization)

        for eq_name in available_eq:
            if remaining_demand <= 0:
                break

            eq_info = equipment_analysis[eq_name]
            current_alloc = allocation.get(eq_name, 0)
            max_possible = eq_info['allocatable_units'] - current_alloc
            if max_possible <= 0:
                continue

            take = min(max_possible, remaining_demand)
            if take > 0:
                allocation[eq_name] = current_alloc + take
                remaining_demand -= take

        return allocation if remaining_demand == 0 else None

    def _get_optimized_equipment_list(self, equipment_analysis, current_allocation, optimization):
        equipment_list = []
        for eq_name, eq_info in equipment_analysis.items():
            current_alloc = current_allocation.get(eq_name, 0)
            remaining_capacity = eq_info['allocatable_units'] - current_alloc
            if remaining_capacity <= 0:
                continue

            if optimization == 'min_cost':
                score = eq_info['hourly_rate']
            elif optimization == 'max_availability':
                score = -remaining_capacity
            else:  # balanced
                score = eq_info['hourly_rate'] * 0.7 + (-remaining_capacity) * 0.3

            equipment_list.append((eq_name, score))

        equipment_list.sort(key=lambda x: x[1])
        return [eq_name for eq_name, _ in equipment_list]

    def _calculate_remaining_capacity(self, equipment_analysis, current_allocation):
        remaining = 0
        for eq_name, eq_info in equipment_analysis.items():
            current_alloc = current_allocation.get(eq_name, 0)
            remaining += max(0, eq_info['allocatable_units'] - current_alloc)
        return remaining

    def _log_allocation_failure(self, task, eq_choices, min_required, equipment_analysis):
        if equipment_analysis:
            available_str = ", ".join([f"{eq}:{info['allocatable_units']}" 
                                       for eq, info in equipment_analysis.items()])
            print(f"Equipment allocation failed - Task: {task.id}, "
                  f"Required: {min_required}, Available: {available_str}")
        else:
            print(f"Equipment allocation failed - Task: {task.id}, "
                  f"No valid equipment in: {eq_choices}")
