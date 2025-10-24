
import streamlit as st
import pandas as pd
from backend.database import SessionLocal
import json
import logging
from datetime import datetime
from sqlalchemy import exists
from sqlalchemy.orm import Session
from backend.db_models import UserBaseTaskDB
from defaults import BASE_TASKS, workers, equipment, disciplines
from backend.database_operations import (
    copy_default_tasks_to_user, save_enhanced_task, duplicate_task, 
    delete_task, get_user_tasks_with_filters, get_user_task_count
)
from helpers import cross_floor_dependecy_ui
logger = logging.getLogger(__name__)


def enhanced_task_management():
    """Professional task management with auto-creation of default tasks"""
    st.subheader("📝 Construction Task Library")
    
    # Get current user ID
    current_user_id = st.session_state["user"]["id"]
    current_username = st.session_state["user"]["username"]
    user_role = st.session_state["user"]["role"]
    
    # ✅ TEMPORARY DEBUG BUTTON - REMOVE LATER
    if st.sidebar.button("🛠️ Debug Task System"):
        debug_task_system()
        return
    
    # Check if user has any tasks
    user_task_count = get_user_task_count(current_user_id)
    
    # Show empty state with import options
    if user_task_count == 0:
        show_empty_state(current_user_id, current_username, user_role)
        return
    
    # User has tasks - show full management interface
    show_task_management_interface(current_user_id, user_role)


def reset_user_tasks_to_default(user_id: int, session, disciplines_to_reset: list = None) -> int:
    """
    Resets user tasks to the default library.
    - disciplines_to_reset: if provided, only resets tasks of those disciplines
    - returns number of tasks restored
    """
    restored_count = 0
    # Fetch existing tasks to avoid duplicates
    existing_tasks = session.query(UserBaseTaskDB).filter_by(user_id=user_id).all()
    existing_keys = {(t.name, t.discipline, t.sub_discipline) for t in existing_tasks}

    for discipline, tasks_list in BASE_TASKS.items():
        if disciplines_to_reset and discipline not in disciplines_to_reset:
            continue
        for t in tasks_list:
            # Unique key check
            key = (t.name, t.discipline, t.sub_discipline)
            if key in existing_keys:
                continue
            # Insert into DB
            user_task = UserBaseTaskDB(
                base_task_id=t.id,
                user_id=user_id,
                name=t.name,
                discipline=t.discipline,
                sub_discipline=t.sub_discipline,
                resource_type=t.resource_type,
                task_type=t.task_type,
                base_duration=t.base_duration or 1,
                min_crews_needed=t.min_crews_needed or 1,
                min_equipment_needed=t.min_equipment_needed or {},
                predecessors=t.predecessors or [],
                repeat_on_floor=t.repeat_on_floor,
                included=True,
                delay=t.delay,
                cross_floor_dependencies=t.cross_floor_dependencies or [],
                applies_to_floors=t.applies_to_floors,
                max_duration=365,
                max_crews=50,
                created_by_user=False,
                creator_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(user_task)
            restored_count += 1

    session.commit()
    return restored_count


def show_task_management_interface(user_id, user_role):
    """
    Top-level management UI for task management.
    - search + discipline filtering
    - selection box + duplicate dialog (asks for new stable ID)
    - reset to defaults (all or by discipline)
    - preserves task editing interface
    """

    # Ensure rerun trigger exists
    if "rerun_trigger" not in st.session_state:
        st.session_state["rerun_trigger"] = False

    # Top action bar
    col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1, 1.5, 1, 1])

    # Search box
    with col1:
        search_term = st.text_input(
            "🔍 Search tasks...", 
            placeholder="Search by name, discipline, or resource type",
            key="task_search"
        )

    # Discipline filter
    with col2:
        discipline_filter = st.multiselect(
            "Discipline",
            options=disciplines,
            default=[],
            key="task_discipline_filter"
        )

    # New Task
    with col3:
        if st.button("➕ New", width='stretch', help="Create new task"):
            st.session_state["creating_new_task"] = True
            st.session_state["editing_task_id"] = None
            st.session_state["rerun_trigger"] = not st.session_state.get("rerun_trigger", False)
            st.rerun()

    # Reset all tasks
    with col4:
        st.markdown("---")
        st.subheader("♻️ Reset User Task Library")
        if st.button("Reset All to Default Tasks", type="secondary", width='stretch'):
            with SessionLocal() as session:
                with st.spinner("🔄 Resetting all tasks to defaults..."):
                    try:
                        restored = reset_user_tasks_to_default(user_id, session)
                        st.success(f"✅ Reset {restored} default tasks successfully!")
                        st.session_state["user_tasks_used"] = False
                        st.session_state["rerun_trigger"] = not st.session_state.get("rerun_trigger", False)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Reset failed: {e}")

    # Reset by discipline
    with col5:
        if st.button("Reset Selected Discipline(s)", type="secondary", width='stretch'):
            if not discipline_filter:
                st.warning("⚠️ Select at least one discipline to reset.")
            else:
                with SessionLocal() as session:
                    with st.spinner("🔄 Resetting selected discipline(s)..."):
                        try:
                            restored = reset_user_tasks_to_default(
                                user_id, session, disciplines_to_reset=discipline_filter
                            )
                            st.success(f"✅ Reset {restored} task(s) for selected discipline(s).")
                            st.session_state["user_tasks_used"] = False
                            st.session_state["rerun_trigger"] = not st.session_state.get("rerun_trigger", False)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Reset by discipline failed: {e}")

    # User Task Count
    with col6:
        task_count = get_user_task_count(user_id)
        st.metric("Your Tasks", task_count)

    # ------------------- Task Editor -------------------
    # Render task editor if editing
    if st.session_state.get("editing_task_id"):
        display_task_editor(user_id)

    # ------------------- Load and Display Tasks -------------------
    tasks = get_user_tasks_with_filters(user_id, search_term, discipline_filter)

    if not tasks:
        st.info("🔍 No tasks match your search criteria. Try different filters or create a new task.")
    else:
        # Normalize fields before display
        for t in tasks:
            if t.min_crews_needed is None:
                t.min_crews_needed = 1
            if t.min_equipment_needed is None:
                t.min_equipment_needed = {}

        display_task_table(tasks, user_id)

    # ------------------- Duplicate Task Handling -------------------
    dup_for = st.session_state.get("duplicate_requested_for")
    if dup_for:
        with SessionLocal() as session:
            original = session.query(UserBaseTaskDB).filter_by(id=dup_for, user_id=user_id).first()

        if original:
            st.markdown("---")
            st.subheader(f"📋 Duplicate Task: {original.name}")
            with st.form(f"duplicate_form_{dup_for}"):
                new_stable_id = st.text_input(
                    "New Stable Task ID (alphanumeric, -, _ allowed)",
                    key=f"dup_id_{dup_for}"
                )
                new_name = st.text_input(
                    "New Name (optional)",
                    value=f"{original.name} (Copy)",
                    key=f"dup_name_{dup_for}"
                )
                submit = st.form_submit_button("Duplicate", width='stretch')
                if submit:
                    ok = duplicate_task(
                        original_task=original,
                        user_id=user_id,
                        new_stable_id=new_stable_id,
                        modifications={"name": new_name}
                    )
                    if ok:
                        st.success(f"✅ Task duplicated as {new_stable_id}")
                        st.session_state.pop("duplicate_requested_for", None)
                        st.session_state["rerun_trigger"] = not st.session_state.get("rerun_trigger", False)
                        st.rerun()
                    else:
                        st.error("❌ Could not duplicate task (see logs).")
        else:
            st.error("Original task not found (it may have been removed).")
            st.session_state.pop("duplicate_requested_for", None)


def _normalize_equipment_dict(equip):
    """
    Ensure equipment dict is JSON-serializable: convert tuple keys -> joined strings,
    ensure integer counts.
    """
    if not equip:
        return {}
    safe = {}
    try:
        for k, v in (equip.items() if isinstance(equip, dict) else []):
            key = "|".join(k) if isinstance(k, (list, tuple)) else str(k)
            try:
                safe[key] = int(v) if v is not None else 0
            except Exception:
                safe[key] = 0
        return safe
    except Exception:
        logger.exception("Failed to normalize equipment dict, returning empty dict.")
        return {}


def display_task_table(tasks, user_id):
    """
    Professional table: shows stable ID (base_task_id) and uses DB PK for internal actions.
    - tasks: list[UserBaseTaskDB]
    """
    if not tasks:
        st.info("📭 No tasks found matching your criteria.")
        return

    # Build DataFrame with stable id shown prominently
    rows = []
    for t in tasks:
        duration_display = "🔄 Calculated" if t.base_duration is None else f"⏱️ {t.base_duration}d"
        equipment_count = len(t.min_equipment_needed) if isinstance(t.min_equipment_needed, dict) else 0
        rows.append({
            "DB_PK": t.id,                      # internal key (hidden from user)
            "Stable ID": getattr(t, "base_task_id", "") or "",
            "Name": t.name,
            "Discipline": t.discipline,
            "Sub": t.sub_discipline or "",
            "Resource": t.resource_type,
            "Duration": duration_display,
            "Crews": t.min_crews_needed,
            "Equipment (#types)": equipment_count,
            "Predecessors": len(t.predecessors or []),
        })

    df = pd.DataFrame(rows)

    # Show a polished table with stable id visible; hide the DB_PK column visually by not showing it in UI
    # We still keep DB_PK in the dataframe object for mapping selection indices -> DB PKs.
    # Use st.dataframe to show the user-facing part:
    st.dataframe(
        df.drop(columns=["DB_PK"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Stable ID": st.column_config.TextColumn("Stable ID", width="small"),
            "Name": st.column_config.TextColumn("Task Name", width="large"),
            "Discipline": st.column_config.TextColumn("Discipline", width="medium"),
            "Sub": st.column_config.TextColumn("Sub-discipline", width="small"),
            "Resource": st.column_config.TextColumn("Resource", width="small"),
            "Duration": st.column_config.TextColumn("Duration", width="small"),
            "Crews": st.column_config.NumberColumn("Crews", width="small"),
            "Equipment (#types)": st.column_config.NumberColumn("Equipment", width="small"),
            "Predecessors": st.column_config.NumberColumn("Predecessors", width="small"),
        }
    )

    # For action widgets we need a reliable selection mechanism:
    # Create a mapping label -> DB_PK so buttons below can act on selection.
    options = [f"{r['Stable ID'] or '(no-id)'} — {r['Name']}" for r in rows]
    pk_map = {options[i]: rows[i]["DB_PK"] for i in range(len(options))}

    st.markdown("### 🛠️ Quick Actions")
    selected_label = st.selectbox("Select a task to act on", options, index=0 if options else -1, key="task_selectbox")

    if selected_label:
        selected_pk = pk_map[selected_label]
        # load the selected full object for display/context
        with SessionLocal() as session:
            selected_task = session.query(UserBaseTaskDB).filter_by(id=selected_pk).first()

        col1, col2, col3, col4 = st.columns([1, 1, 1, 2], gap="small")
        with col1:
            if st.button("✏️ Edit", key=f"edit_btn_{selected_pk}", width='stretch'):
                st.session_state["editing_task_id"] = selected_pk
                st.session_state["creating_new_task"] = False
                st.rerun()
        with col2:
            if st.button("📋 Duplicate", key=f"dup_btn_{selected_pk}", width='stretch'):
                # open duplicate form inline below (see show_task_management_interface)
                st.session_state["duplicate_requested_for"] = selected_pk
                st.rerun()
        with col3:
            if st.button("🗑️ Delete", key=f"del_btn_{selected_pk}", width='stretch'):
                # two-step confirm
                confirm_key = f"confirm_del_{selected_pk}"
                if st.session_state.get(confirm_key):
                    ok = delete_task(selected_pk, user_id)
                    st.session_state.pop(confirm_key, None)
                    if ok:
                        st.success("✅ Task deleted")
                        st.rerun()
                    else:
                        st.error("❌ Delete failed")
                else:
                    st.session_state[confirm_key] = True
                    st.warning("Click Delete again to confirm")
        with col4:
            # Summary box for selected task
            st.markdown(f"**Selected:** `{selected_task.name}` — Stable ID: `{getattr(selected_task, 'base_task_id', '')}`")
            st.caption(f"{selected_task.discipline} / {selected_task.sub_discipline or '—'} • {selected_task.resource_type}")


def show_empty_state(user_id, username, user_role):
    """Show empty state with import options - ENHANCED VERSION"""
    st.warning("🎯 No personal tasks found in your library.")
    
    # Show creation options
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🚀 Import Default Tasks")
        st.markdown("""
        - Get 50+ pre-configured tasks
        - Mix of calculated and fixed durations
        - Based on industry standards
        - Fully customizable afterward
        """)
        if st.button("📥 Import Default Tasks", width='stretch', key="import_defaults_main"):
            with st.spinner("Importing default construction tasks..."):
                # FIX: Use database session
                with SessionLocal() as session:
                    created_count = copy_default_tasks_to_user(user_id, session)  # ← ADD SESSION
                    if created_count > 0:
                        st.success(f"✅ Imported {created_count} default tasks to your library!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ No default tasks available to import")
    
    with col2:
        st.markdown("#### 🆕 Start Fresh")
        st.markdown("""
        - Create tasks from scratch
        - Choose calculated or fixed durations
        - Build custom resource types
        - Complete control
        """)
        if st.button("✨ Create First Task", width='stretch', key="create_first_main"):
            st.session_state["creating_new_task"] = True
            st.session_state["editing_task_id"] = None
            st.rerun()
    
    st.markdown("---")
    st.info("""
    💡 **About Duration Types:**
    - **🔄 Calculated**: Scheduling engine calculates duration based on quantities and productivity rates
    - **⏱️ Fixed**: You set a specific duration that won't be changed by the engine
    """)


def display_task_editor(user_id):
    """Comprehensive task editor with duration type selection"""
    editing_task_id = st.session_state.get("editing_task_id")
    creating_new = st.session_state.get("creating_new_task", False)
    
    with SessionLocal() as session:
        if editing_task_id:
            task = session.query(UserBaseTaskDB).filter_by(id=editing_task_id, user_id=user_id).first()
            is_new = False
            title = "✏️ Edit Task"
            if not task:
                st.error("Task not found")
                return
        else:
            task = None
            is_new = True
            title = "➕ Create New Task"
        
        st.subheader(title)
        
        with st.form(f"task_editor_{user_id}"):
            # Basic Information Section
            st.markdown("### 📋 Basic Information")
            col1, col2, col3 = st.columns(3)
            with col1:
                task_name = st.text_input(
                    "Task Name *", 
                    value=task.name if task else "",
                    placeholder="e.g., Concrete Foundation Work",
                    help="Descriptive name for the construction task"
                )
            with col2:
                discipline = st.selectbox(
                    "Discipline *", 
                    disciplines,
                    index=disciplines.index(task.discipline) if task and task.discipline in disciplines else 0
                )
            with col3:
                # ✅ FLEXIBLE: Free-text resource type input
                current_resource = task.resource_type if task else "BétonArmée"
                resource_type = st.text_input(
                    "Resource Type *",
                    value=current_resource,
                    placeholder="e.g., Topograph, Maçonnerie, etc.",
                    help="Enter any resource type. Users can create custom types."
                )
            
            # Duration Configuration with Type Selection
            st.markdown("### ⏱️ Duration Configuration")
            
            # Get current duration info
            if task and task.base_duration is None:
                current_duration_type = "calculated"
                current_duration_value = None
            else:
                current_duration_type = "fixed" 
                current_duration_value = float(task.base_duration) if task and task.base_duration else 1.0
            
            col1, col2 = st.columns(2)
            with col1:
                duration_type = st.radio(
                    "Duration Type:",
                    options=["calculated", "fixed"],
                    format_func=lambda x: {
                        "calculated": "🔄 Calculated by Scheduling Engine",
                        "fixed": "⏱️ Fixed Duration (Manual)"
                    }[x],
                    index=0 if current_duration_type == "calculated" else 1,
                    help="""
                    **Calculated**: Scheduling engine will calculate duration based on quantities and productivity rates.
                    **Fixed**: You set a specific duration that won't be changed by the engine.
                    """
                )
            
            with col2:
                if duration_type == "fixed":
                    base_duration = st.number_input(
                        "Fixed Duration (days) *",
                        min_value=0.1, max_value=365.0, step=0.5,
                        value=current_duration_value,
                        help="Manual duration that won't be calculated by scheduling engine"
                    )
                else:
                    base_duration = None
                    st.info("🔄 Duration will be calculated by scheduling engine based on quantities and productivity rates")
            
            # Resource Requirements
            st.markdown("### 👥 Resource Requirements")
            col1, col2, col3 = st.columns(3)
            with col1:
                min_crews_needed = st.number_input(
                    "Minimum Crews *",
                    min_value=1, max_value=50, step=1,
                    value=task.min_crews_needed if task and task.min_crews_needed else 1,
                    help="Number of crew teams required"
                )
            with col2:
                delay = st.number_input(
                    "Delay (days)",
                    min_value=0, max_value=30, step=1,
                    value=task.delay if task and task.delay else 0,
                    help="Mandatory delay after predecessor completion"
                )
            with col3:
                task_type = st.selectbox(
                    "Task Type",
                    ["worker", "equipment", "hybrid"],
                    index=["worker", "equipment", "hybrid"].index(task.task_type) 
                    if task and task.task_type else 0
                )
            
            # Equipment Requirements
            st.markdown("### 🚜 Equipment Requirements")
            equipment_options = ["None", "Crane", "Excavator", "Concrete Pump", "Bulldozer", "Other"]
            selected_equipment = st.multiselect(
                "Required Equipment",
                equipment_options,
                default=[],
                help="Select equipment needed for this task"
            )
            
            # Convert to your equipment format
            min_equipment_needed = {eq: 1 for eq in selected_equipment if eq != "None"}
            
            # Task Dependencies
            st.markdown("### ⏩ Task Dependencies")
            available_tasks = session.query(UserBaseTaskDB).filter(
                UserBaseTaskDB.user_id == user_id,
                UserBaseTaskDB.id != (task.id if task else None)
            ).all()
            
            predecessor_options = [f"{t.name} ({t.discipline})" for t in available_tasks]
            selected_predecessors = st.multiselect(
                "Predecessor Tasks",
                predecessor_options,
                default=[],
                help="Tasks that must complete before this one starts"
            )
            
            # Convert back to task IDs for storage
            predecessor_ids = []
            for pred_name in selected_predecessors:
                for t in available_tasks:
                    if f"{t.name} ({t.discipline})" == pred_name:
                        predecessor_ids.append(t.id)
                        break
            
            # Cross-Floor Configuration - FIXED: Added missing function parameter
            st.markdown("### 🏢 Cross-Floor Configuration")
            cross_floor_config = {}  # Placeholder - you'll need to implement cross_floor_dependency_ui function
            
            # Advanced Settings
            with st.expander("⚙️ Advanced Settings"):
                col1, col2 = st.columns(2)
                with col1:
                    repeat_on_floor = st.checkbox(
                        "Repeat on each floor",
                        value=task.repeat_on_floor if task else True
                    )
                with col2:
                    included = st.checkbox(
                        "Include in scheduling",
                        value=task.included if task else True,
                        help="Uncheck to exclude this task from scheduling"
                    )
            
            # Form Actions
            st.markdown("---")
            
            # Show summary of choices
            if duration_type == "calculated":
                st.info("🎯 **This task will have its duration calculated automatically by the scheduling engine**")
            else:
                st.info(f"🎯 **This task has a fixed duration of {base_duration} days**")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.form_submit_button("💾 Save Task", width='stretch'):
                    if not task_name:
                        st.error("❌ Task name is required")
                    elif not resource_type:
                        st.error("❌ Resource type is required")
                    else:
                        success = save_enhanced_task(
                            session, task, is_new, user_id, task_name, discipline, 
                            resource_type, base_duration, min_crews_needed, delay,
                            min_equipment_needed, predecessor_ids, cross_floor_config,
                            task_type, repeat_on_floor, included
                        )
                        if success:
                            st.session_state.pop("editing_task_id", None)
                            st.session_state.pop("creating_new_task", None)
                            st.rerun()
            with col2:
                if st.form_submit_button("❌ Cancel", width='stretch'):
                    st.session_state.pop("editing_task_id", None)
                    st.session_state.pop("creating_new_task", None)
                    st.rerun()
            with col3:
                if task and st.form_submit_button("📋 Save as Copy", width='stretch'):
                    success = duplicate_task(
                        original_task=task,
                        user_id=user_id,
                        new_stable_id=f"{task.base_task_id}_copy",
                        modifications={
                            'name': f"{task_name} (Copy)",
                            'base_duration': base_duration,
                            'min_crews_needed': min_crews_needed,
                            'resource_type': resource_type
                        }
                    )
                    if success:
                        st.session_state.pop("editing_task_id", None)
                        st.session_state.pop("creating_new_task", None)
                        st.rerun()


def debug_task_system():
    """Debug function to check what's happening with tasks"""
    with SessionLocal() as session:
        # Check different types of tasks
        total_tasks = session.query(UserBaseTaskDB).count()
        system_tasks = session.query(UserBaseTaskDB).filter_by(created_by_user=False).count()
        user_tasks = session.query(UserBaseTaskDB).filter_by(created_by_user=True).count()
        
        st.write(f"🔍 DEBUG - Total tasks in DB: {total_tasks}")
        st.write(f"🔍 DEBUG - System default tasks: {system_tasks}")
        st.write(f"🔍 DEBUG - User custom tasks: {user_tasks}")
        
        # Show some example tasks
        example_tasks = session.query(UserBaseTaskDB).limit(5).all()
        for task in example_tasks:
            st.write(f" - {task.name} (User: {task.user_id}, System: {not task.created_by_user})")
