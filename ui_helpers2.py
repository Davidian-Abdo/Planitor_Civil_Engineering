import streamlit as st
import pandas as pd
from backend.database import SessionLocal
from backend.db_models import UserBaseTasks
from defaults import BaseTasks,workers,equipment
from backend.database_operations import (
    copy_default_tasks_to_user, save_enhanced_task, duplicate_task, 
    delete_task, get_user_tasks_with_filters, get_user_task_count
)
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

def reset_user_tasks_to_defaults(user_id):
    """Reset all default tasks for a user without duplicates"""
    with SessionLocal() as session:
        # Get existing stable IDs for this user
        existing_ids = {
            t.base_task_id for t in session.query(UserBaseTaskDB)
            .filter(UserBaseTaskDB.user_id == user_id)
            .all()
        }

        new_tasks = []
        for discipline, task_list in BASE_TASKS.items():
            for base_task in task_list:
                if base_task.id not in existing_ids:
                    new_task = UserBaseTaskDB(
                        user_id=user_id,
                        task_id=base_task.id,
                        name=base_task.name,
                        discipline=base_task.discipline,
                        sub_discipline=base_task.sub_discipline,
                        resource_type=base_task.resource_type,
                        task_type=base_task.task_type,
                        base_duration=base_task.base_duration,
                        min_crews_needed=getattr(base_task, "min_crews_needed", 1),
                        min_equipment_needed=getattr(base_task, "min_equipment_needed", {}),
                        predecessors=base_task.predecessors,
                        repeat_on_floor=getattr(base_task, "repeat_on_floor", True),
                        created_by_user=False
                    )
                    new_tasks.append(new_task)

        if new_tasks:
            session.add_all(new_tasks)
            session.commit()
            return len(new_tasks)
        return 0
def show_task_management_interface(user_id, user_role):
    """Display full task management interface with search, filters, and task actions"""
    # Top action bar
    col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])

    with col1:
        search_term = st.text_input("🔍 Search tasks...", placeholder="Search by name, discipline, or resource type")

    with col2:
        discipline_filter = st.multiselect("Discipline", disciplines, default=[], placeholder="All")

    with col3:
        if st.button("➕ New", use_container_width=True, help="Create new task"):
            st.session_state["creating_new_task"] = True
            st.session_state["editing_task_id"] = None

    with col4:
        if st.button("📥 Import", use_container_width=True, help="Import from templates"):
            show_import_template_modal(user_id)

    with col5:
        if st.button("🔄 Reset to Default Tasks", use_container_width=True):
            count = reset_user_tasks_to_defaults(user_id)
            if count:
                st.success(f"✅ Imported {count} default tasks!")
            else:
                st.info("All default tasks already exist in your library.")
            st.rerun()

    with col6:
        task_count = get_user_task_count(user_id)
        st.metric("Your Tasks", task_count)

    # Load and display tasks
    tasks = get_user_tasks_with_filters(user_id, search_term, discipline_filter)

    if not tasks:
        st.info("🔍 No tasks match your search criteria. Try different filters or create a new task.")
        return

    # Display tasks table with actions
    display_task_table(tasks, user_id)

    # Task editor (create or edit)
    if st.session_state.get("editing_task_id") or st.session_state.get("creating_new_task"):
        st.markdown("---")
        with SessionLocal() as session:
            display_task_editor(session, user_id)


def display_task_table(tasks, user_id):
    """Display tasks as a professional table with actions (supports duplication with base_task_id)"""
    if not tasks:
        st.info("📭 No tasks found matching your criteria.")
        return

    task_data = []
    for task in tasks:
        duration_display = f"⏱️ {task.base_duration}d" if task.base_duration else "🔄 Calculated"
        task_data.append({
            "ID": task.base_task_id,
            "Name": task.name,
            "Discipline": task.discipline,
            "Resource": task.resource_type,
            "Duration": duration_display,
            "Crews": task.min_crews_needed,
            "Equipment": len(task.min_equipment_needed) if task.min_equipment_needed else 0,
            "Predecessors": len(task.predecessors or []),
            "Cross-Floor": len(task.cross_floor_dependencies or [])
        })

    df = pd.DataFrame(task_data)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("Task ID", width="small"),
            "Name": st.column_config.TextColumn("Task Name", width="large"),
            "Discipline": st.column_config.TextColumn("Discipline", width="medium"),
            "Resource": st.column_config.TextColumn("Resource", width="medium"),
            "Duration": st.column_config.TextColumn("Duration", width="small"),
            "Crews": st.column_config.NumberColumn("Crews", width="small"),
            "Equipment": st.column_config.NumberColumn("Equipment", width="small"),
            "Predecessors": st.column_config.NumberColumn("Predecessors", width="small"),
            "Cross-Floor": st.column_config.NumberColumn("Cross-Floor", width="small"),
        }
    )

    st.markdown("### 🛠️ Quick Actions")
    for task in tasks:
        with st.expander(f"Actions for '{task.name}'"):
            st.write(f"**ID:** {task.base_task_id}")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✏️ Edit", key=f"edit_{task.base_task_id}", use_container_width=True):
                    st.session_state["editing_task_id"] = task.id
                    st.session_state["creating_new_task"] = False
                    st.rerun()
            with col2:
                with st.form(f"duplicate_form_{task.base_task_id}"):
                    new_base_task_id = st.text_input("New Task ID (unique & alphanumeric)", key=f"dup_id_{task.base_task_id}")
                    new_name = st.text_input("Optional new task name", f"{task.name} (Copy)", key=f"dup_name_{task.base_task_id}")
                    submit = st.form_submit_button("Duplicate")
                    if submit:
                        if not new_base_task_id:
                            st.error("Please enter a new Task ID")
                        else:
                            success = duplicate_task(
                                original_task=task,
                                user_id=user_id,
                                new_base_task_id=new_base_task_id,
                                modifications={"name": new_name}
                            )
                            if success:
                                st.success(f"✅ Task duplicated as '{new_base_task_id}'")
                                st.rerun()
                            else:
                                st.error("❌ Failed to duplicate task")
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{task.base_task_id}", use_container_width=True):
                    if st.session_state.get(f"confirm_delete_{task.base_task_id}"):
                        if delete_task(task.id, user_id):
                            st.success("✅ Task deleted!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete task")
                    else:
                        st.session_state[f"confirm_delete_{task.base_task_id}"] = True
                        st.warning("Click again to confirm deletion")
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
        if st.button("📥 Import Default Tasks", use_container_width=True, key="import_defaults_main"):
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
        if st.button("✨ Create First Task", use_container_width=True, key="create_first_main"):
            st.session_state["creating_new_task"] = True
            st.session_state["editing_task_id"] = None
            st.rerun()
    
    st.markdown("---")
    st.info("""
    💡 **About Duration Types:**
    - **🔄 Calculated**: Scheduling engine calculates duration based on quantities and productivity rates
    - **⏱️ Fixed**: You set a specific duration that won't be changed by the engine
    """)

def display_task_editor(session, user_id):
    """Comprehensive task editor with duration type selection"""
    editing_task_id = st.session_state.get("editing_task_id")
    creating_new = st.session_state.get("creating_new_task", False)
    
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
        
        # Cross-Floor Configuration
        st.markdown("### 🏢 Cross-Floor Configuration")
        cross_floor_config = cross_floor_dependency_ui(task) if task else {}
        
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
            if st.form_submit_button("💾 Save Task", use_container_width=True):
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
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state.pop("editing_task_id", None)
                st.session_state.pop("creating_new_task", None)
                st.rerun()
        with col3:
            if task and st.form_submit_button("📋 Save as Copy", use_container_width=True):
                success = duplicate_task(task, user_id, modifications={
                    'name': f"{task_name} (Copy)",
                    'base_duration': base_duration,
                    'min_crews_needed': min_crews_needed,
                    'resource_type': resource_type
                })
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

def create_default_tasks_now():
    """One-time function to create default tasks in database"""
    st.subheader("🚀 Create Default Tasks Now")
    
    current_user_id = st.session_state["user"]["id"]
    
    if st.button("🎯 Create Default Construction Tasks in Database", type="primary"):
        try:
            with st.spinner("Creating default construction tasks from defaults.py..."):
                # Import the function
                from backend.database_operations import create_default_tasks_from_defaults_py
                
                # Create system default tasks (with user_id=None)
                with SessionLocal() as session:
                    user_count = copy_default_tasks_to_user(current_user_id, session)
                
                if created_count > 0:
                    st.success(f"✅ Created {created_count} system default tasks!")
                    # Now copy them to current user
                    from backend.database_operations import copy_default_tasks_to_user
                    user_count = copy_default_tasks_to_user(current_user_id)
                    if user_count > 0:
                        st.success(f"✅ Copied {user_count} tasks to your personal library!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.info("Tasks created but couldn't copy to user (might already exist)")
                else:
                    st.error("❌ Could not create default tasks") 
        except Exception as e:
            st.error(f"❌ Error: {e}")
            import traceback
            st.code(traceback.format_exc())
