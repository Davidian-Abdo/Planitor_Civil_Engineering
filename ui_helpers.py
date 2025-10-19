import streamlit as st
from defaults import disciplines
from models import DisciplineZoneConfig


def get_all_users():
    """Get list of all users for admin management"""
    return [st.session_state["user"]["username"]]

def save_user_task(task, is_new, user_id, task_name, discipline, resource_type, 
                  base_duration, min_crews_needed, cross_floor_config, selected_predecessors):
    """Save user task to database"""
    try:
        with SessionLocal() as session:
            if is_new:
                new_task = UserBaseTaskDB(
                    user_id=user_id,
                    name=task_name,
                    discipline=discipline,
                    resource_type=resource_type,
                    base_duration=base_duration,
                    min_crews_needed=min_crews_needed,
                    created_by_user=True
                )
                session.add(new_task)
            else:
                # Update existing task
                task.name = task_name
                task.discipline = discipline
                task.resource_type = resource_type
                task.base_duration = base_duration
                task.min_crews_needed = min_crews_needed
            
            session.commit()
            st.success("✅ Task saved successfully!")
            st.session_state.pop("editing_task_id", None)
            st.session_state.pop("creating_new_task", None)
            st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to save task: {e}")

def display_user_task_card(task, user_id):
    """Display task card in the task list"""
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{task.name}**")
            st.caption(f"{task.discipline} • {task.resource_type} • {task.base_duration}d")
        with col2:
            st.write(f"👷 {task.min_crews_needed}")
        with col3:
            if st.button("✏️", key=f"edit_{task.id}"):
                st.session_state["editing_task_id"] = task.id
                st.rerun()
        st.divider()

def show_import_template_modal(user_id):
    """Show import template modal"""
    st.info("📥 Import functionality would go here")

# SIMPLIFIED CONSTRAINT MANAGER PLACEHOLDER
class SimpleConstraintManager:
    def get_default_value(self, constraint_type, discipline):
        return 1.0 if constraint_type == "duration" else 1
    
    def validate_task_data(self, task_data, discipline):
        return []  # No validation errors for now


def user_specific_task_management():
    """Task management for individual users with constraints"""
    
    st.subheader("📝 Manage Your Task Library")
    
    # Get current user
    current_user = st.session_state["user"]["username"]
    user_role = st.session_state["user"]["role"]
    
    # Admin can see all users, others only see their own
    if user_role == "admin":
        st.info("👑 Admin View: You can manage all user task libraries")
        all_users = get_all_users()
        selected_user = st.selectbox("Select User to Manage:", all_users, index=all_users.index(current_user))
        target_user = selected_user
    else:
        target_user = current_user
        st.info(f"👤 Managing your personal task library")
    # Two-column layout
    col_list, col_editor = st.columns([2, 3])
    with col_list:
        show_user_task_list(target_user)
    with col_editor:
        show_constrained_task_editor(target_user)

def show_user_task_list(user_id): 
    """Show tasks for specific user with filtering"""
    st.markdown("### 📋 Your Task Library")
    
    # Quick actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ New Task", use_container_width=True):
            st.session_state["creating_new_task"] = True
    with col2:
        if st.button("📥 Import from Template", use_container_width=True):
            show_import_template_modal(user_id)
    # Filtering
    search_term = st.text_input("🔍 Search your tasks...", placeholder="Search by name or discipline")
    discipline_filter = st.multiselect("Filter by discipline:", disciplines, default=[])
    
    # Load user's tasks
    with SessionLocal() as session:
        user_tasks = session.query(UserBaseTaskDB).filter(
            UserBaseTaskDB.user_id == user_id
        ).order_by(UserBaseTaskDB.discipline, UserBaseTaskDB.name).all()
        
        # Apply filters
        if search_term:
            user_tasks = [t for t in user_tasks if search_term.lower() in t.name.lower()]
        if discipline_filter:
            user_tasks = [t for t in user_tasks if t.discipline in discipline_filter]
        
        # Display tasks
        for task in user_tasks:
            display_user_task_card(task, user_id)

def organize_tasks_by_discipline(user_tasks):
    """
    Convert list of BaseTaskDB objects to discipline-organized format
    expected by template generation and scheduling
    """
    tasks_by_discipline = {}
    
    for task in user_tasks:
        if task.discipline not in tasks_by_discipline:
            tasks_by_discipline[task.discipline] = []
        
        # Convert to dictionary format
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
            # Include cross-floor configuration if available
            'cross_floor_dependencies': getattr(task, 'cross_floor_dependencies', []),
            'applies_to_floors': getattr(task, 'applies_to_floors', 'auto'),
            'task_type': getattr(task, 'task_type', 'worker')
        }
        
        tasks_by_discipline[task.discipline].append(task_dict)
    
    return tasks_by_discipline


def show_constrained_task_editor(user_id):
    """Task editor with constraint validation"""
    editing_task_id = st.session_state.get("editing_task_id")
    creating_new = st.session_state.get("creating_new_task", False)
    
    if not editing_task_id and not creating_new:
        st.info("👈 Select a task from your library to edit, or create a new one")
        return
    
    with SessionLocal() as session:
        if editing_task_id:
            task = session.query(UserBaseTaskDB).filter(
                UserBaseTaskDB.id == editing_task_id,
                UserBaseTaskDB.user_id == user_id
            ).first()
            is_new = False
        else:
            task = UserBaseTaskDB(user_id=user_id)
            is_new = True
        
        with st.form(f"task_form_{user_id}_{task.id if task.id else 'new'}"):
            st.markdown("### ✏️ Task Editor with Validation")
            
            # Basic Information with Constraints
            st.markdown("**📝 Basic Information**")
            col1, col2 = st.columns(2)
            
            with col1:
                task_name = st.text_input("Task Name", 
                    value=task.name if task else "",
                    max_chars=255,
                    help="Descriptive name for the task"
                )
                
                discipline = st.selectbox("Discipline", disciplines, 
                    index=disciplines.index(task.discipline) if task and task.discipline else 0
                )
            
            with col2:
                resource_type = st.selectbox("Resource Type", ["worker", "equipment", "hybrid"],
                    index=["worker", "equipment", "hybrid"].index(task.resource_type) if task and task.resource_type else 0
                )
                
                # Duration with constraints
                default_duration = constraint_manager.get_default_value("duration", discipline) or 1.0
                min_duration = constraint_manager.constraints.get(f"duration_{discipline}") or constraint_manager.constraints.get("duration_global")
                max_duration = constraint_manager.constraints.get(f"duration_{discipline}") or constraint_manager.constraints.get("duration_global")
                
                base_duration = st.number_input("Base Duration (days)", 
                    min_value=float(min_duration.min_value) if min_duration else 0.1,
                    max_value=float(max_duration.max_value) if max_duration else 365.0,
                    value=task.base_duration if task and task.base_duration else default_duration,
                    step=0.5,
                    help=f"Allowed range: {min_duration.min_value if min_duration else 0.1} - {max_duration.max_value if max_duration else 365.0} days"
                )
            
            # Crews with constraints
            st.markdown("**👷 Resource Requirements**")
            col1, col2 = st.columns(2)
            with col1:
                default_crews = constraint_manager.get_default_value("crews", discipline) or 1
                min_crews = constraint_manager.constraints.get(f"crews_{discipline}") or constraint_manager.constraints.get("crews_global")
                max_crews = constraint_manager.constraints.get(f"crews_{discipline}") or constraint_manager.constraints.get("crews_global")
                
                min_crews_needed = st.number_input("Minimum Crews", 
                    min_value=int(min_crews.min_value) if min_crews else 1,
                    max_value=int(max_crews.max_value) if max_crews else 50,
                    value=task.min_crews_needed if task and task.min_crews_needed else default_crews,
                    step=1,
                    help=f"Allowed range: {min_crews.min_value if min_crews else 1} - {max_crews.max_value if max_crews else 50} crews"
                )
            
            # Cross-floor configuration
            st.markdown("**🔄 Cross-Floor Configuration**")
            cross_floor_config = cross_floor_dependency_ui(task) if task else {}
            
            # Predecessors with constraint
            st.markdown("**⏩ Predecessor Tasks**")
            with SessionLocal() as inner_session:
                user_tasks = inner_session.query(UserBaseTaskDB).filter(
                    UserBaseTaskDB.user_id == user_id,
                    UserBaseTaskDB.id != getattr(task, 'id', None)
                ).all()
                predecessor_options = [f"{t.name} ({t.discipline})" for t in user_tasks]
                selected_predecessors = st.multiselect("Select predecessor tasks:", 
                    predecessor_options,
                    help="Maximum 10 predecessors allowed"
                )
            
            # Form submission with validation
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Task", use_container_width=True):
                    # Prepare task data for validation
                    task_data = {
                        'base_duration': base_duration,
                        'min_crews_needed': min_crews_needed,
                        'predecessors': selected_predecessors
                    }
                    
                    # Validate against constraints
                    validation_errors = constraint_manager.validate_task_data(task_data, discipline)
                    
                    if validation_errors:
                        for error in validation_errors:
                            st.error(error)
                    else:
                        save_user_task(task, is_new, user_id, task_name, discipline, resource_type, 
                                     base_duration, min_crews_needed, cross_floor_config, selected_predecessors)
            
            with col2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.pop("editing_task_id", None)
                    st.session_state.pop("creating_new_task", None)
                    st.rerun()



def generate_user_cross_floor_dependencies(base_task, zone, floor, task_ids, base_by_id):
    dependencies = []
    
    # PROCESS USER-CONFIGURED CROSS-FLOOR DEPENDENCIES
    user_deps = getattr(base_task, 'cross_floor_dependencies', []) or []
    
    for dep_config in user_deps:
        pred_id = dep_config.get('task_id')        # Which task to depend on
        floor_offset = dep_config.get('floor_offset', -1)  # Floor relationship
        
        pred_base = base_by_id.get(pred_id)
        if pred_base and getattr(pred_base, "included", True):
            pred_floor = floor + floor_offset  # Calculate target floor
            
            # Check if predecessor can exist on this floor
            if is_valid_floor_for_task(pred_base, pred_floor, zone):
                dependency_id = f"{pred_id}-F{pred_floor}-{zone}"
                if dependency_id in task_ids:
                    dependencies.append(dependency_id)
    return dependencies
    
def cross_floor_dependency_ui(base_task): 
    """Simple UI for configuring cross-floor dependencies"""
    
    st.markdown("### 🔄 Cross-Floor Dependencies")
    st.info("Configure tasks from **other floors** that this task depends on")
    
    # Get current dependencies
    current_deps = getattr(base_task, 'cross_floor_dependencies', []) or []
    
    # Display current dependencies
    if current_deps:
        st.markdown("**Current Cross-Floor Dependencies:**")
        for i, dep in enumerate(current_deps):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                dep_task = get_task_by_id(dep['task_id'])
                st.write(f"**{dep_task.name if dep_task else dep['task_id']}**")
            with col2:
                floor_text = get_floor_offset_text(dep['floor_offset'])
                st.write(floor_text)
            with col3:
                st.write("🔗" if dep.get('required', True) else "⚡")
            with col4:
                if st.button("❌", key=f"remove_{i}"):
                    remove_cross_floor_dependency(base_task, dep['task_id'])
                    st.rerun()
    
    # Add new dependency
    with st.expander("➕ Add Cross-Floor Dependency", expanded=len(current_deps) == 0):
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            available_tasks = get_available_dependency_tasks(base_task)
            task_options = {f"{t.name} ({t.discipline})": t.id for t in available_tasks}
            selected_task = st.selectbox(
                "Task depends on:",
                options=list(task_options.keys()),
                key="new_dep_task"
            )
        with col2:
            floor_offset = st.selectbox(
                "Floor relationship:",
                options=[-2, -1, 1, 2],
                format_func=lambda x: {
                    -2: "📥 2 Floors Below",
                    -1: "📥 Floor Below", 
                    1: "📤 Floor Above",
                    2: "📤 2 Floors Above"
                }[x],
                index=1,  # Default to "Floor Below"
                key="new_dep_floor"
            )
        with col3:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("Add", key="add_dep"):
                if selected_task:
                    task_id = task_options[selected_task]
                    add_cross_floor_dependency(base_task, task_id, floor_offset)
                    st.rerun()
        # Simple floor application override
    st.markdown("### 🏢 Floor Application")
    applies_to_floors = st.selectbox(
        "Generate task for:",
        options=["auto", "ground_only", "above_ground", "all_floors"],
        format_func=lambda x: {
            "auto": "🤖 Auto (use existing rules)",
            "ground_only": "🌱 Ground floor only", 
            "above_ground": "⬆️ Above ground only",
            "all_floors": "🏢 All floors including ground"
        }[x],
        index=["auto", "ground_only", "above_ground", "all_floors"].index(
            getattr(base_task, 'applies_to_floors', 'auto')
        )
    )
    
    return {
        "cross_floor_dependencies": current_deps,
        "applies_to_floors": applies_to_floors
    }

def render_discipline_zone_config(disciplines, zones, key_prefix="disc_zone_cfg"):
    """
    Renders a UI to configure zones per discipline:
    - User can select zones to run in parallel or sequential groups
    Returns dict: {discipline: DisciplineZoneConfig}
    """
    cfg = {}
    for disc in disciplines:
        st.markdown(f"### Discipline: {disc}")
        with st.expander(f"Configure zone execution for {disc}", expanded=False):
            st.markdown("Select zones to run in **parallel groups** or **sequentially**:")
            selected_strategy = st.radio(
                f"Execution type ({disc})",
                options=["sequential", "fully_parallel"],
                key=f"{key_prefix}_strategy_{disc}"
            )
            group_text = st.text_area(
                f"Zone Groups ({disc})",
                value=",".join(zones),
                help="Enter zones separated by commas for first group; use new lines for multiple groups",
                key=f"{key_prefix}_groups_{disc}"
            )
            # Parse into list of lists
            zone_groups = []
            for line in group_text.strip().split("\n"):
                group = [z.strip() for z in line.split(",") if z.strip()]
                if group:
                    zone_groups.append(group)

            cfg[disc] = DisciplineZoneConfig(
                discipline=disc,
                zone_groups=zone_groups,
                strategy=selected_strategy
            )
    return cfg

def inject_ui_styles():
    """Inject professional UI styles"""
    st.markdown("""
    <style>
    /* Enhanced tab styling */
    .enhanced-tab {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin: 0.5rem 0;
    }
    
    /* File upload styling */
    .uploaded-file {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    
    /* Status indicators */
    .status-ready { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-error { color: #dc3545; font-weight: bold; }
    
    /* Progress bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
    }
    
    /* DataFrame styling */
    .dataframe {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Button group styling */
    .button-group {
        display: flex;
        gap: 10px;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

def create_metric_row(metrics_dict):
    """Create a row of professional metric cards"""
    cols = st.columns(len(metrics_dict))
    for idx, (title, value) in enumerate(metrics_dict.items()):
        with cols[idx]:
            st.markdown(f"""
            <div class="metric-container">
                <div style="font-size: 0.9rem; opacity: 0.9;">{title}</div>
                <div style="font-size: 1.8rem; font-weight: bold;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

def create_info_card(title, content, icon="ℹ️", card_type="info"):
    """Create professional information cards"""
    colors = {
        "info": "#1f77b4",
        "success": "#28a745", 
        "warning": "#ffc107",
        "error": "#dc3545"
    }
    
    st.markdown(f"""
    <div class="professional-card" style="border-left-color: {colors[card_type]};">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <span style="font-size: 1.5rem;">{icon}</span>
            <h4 style="margin: 0; color: {colors[card_type]};">{title}</h4>
        </div>
        <div style="color: #555;">{content}</div>
    </div>
    """, unsafe_allow_html=True)

def render_upload_section(title, key_suffix, accepted_types=["xlsx","xls","csv"]):
    """Enhanced file upload section"""
    with st.container():
        st.markdown(f"**{title}**")
        
        uploaded_file = st.file_uploader(
            f"Upload {title}",
            type=accepted_types,
            key=f"upload_{key_suffix}",
            help=f"Upload your {title} file in Excel format"
        )
        
        if uploaded_file:
            file_size = uploaded_file.size / 1024 / 1024  # Convert to MB
            file_details = {
                "name": uploaded_file.name,
                "size": f"{file_size:.2f} MB",
                "type": uploaded_file.type
            }
            
            st.markdown(f"""
            <div class="uploaded-file">
                <strong>✅ {uploaded_file.name}</strong><br>
                <small>Size: {file_size:.2f} MB | Type: {uploaded_file.type}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # Only keep the upper limit check
            if file_size < 0.005:
                st.error("❌ File size exceeds 50MB limit.")
                return None
            if file_size > 30:
                st.error("❌ File size exceeds 50MB limit.")
                return None
            
            return uploaded_file  # ✅ CRITICAL: Return the file object
        
        return None
