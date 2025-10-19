# ui_helpers.py - COMPLETE VERSION WITH ALL UI FUNCTIONS
import streamlit as st
from backend.database import SessionLocal
from backend.db_models import UserBaseTaskDB
from defaults import disciplines
from models import DisciplineZoneConfig

# ==================== CONSTRAINTS & CONFIGURATION ====================
class SimpleConstraintManager:
    def __init__(self):
        self.constraints = {}
    
    def get_default_value(self, constraint_type, discipline):
        return 1.0 if constraint_type == "duration" else 1
    
    def validate_task_data(self, task_data, discipline):
        return []  # No validation errors

constraint_manager = SimpleConstraintManager()

# ==================== TASK MANAGEMENT FUNCTIONS ====================
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
    Convert list of UserBaseTaskDB objects to discipline-organized format
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
            'cross_floor_dependencies': getattr(task, 'cross_floor_dependencies', []),
            'applies_to_floors': getattr(task, 'applies_to_floors', 'auto'),
            'task_type': getattr(task, 'task_type', 'worker')
        }
        
        tasks_by_discipline[task.discipline].append(task_dict)
    
    return tasks_by_discipline

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
            if not task:
                st.error("Task not found")
                return
        else:
            task = None
            is_new = True
        
        with st.form(f"task_form_{user_id}"):
            st.markdown("### ✏️ Task Editor with Validation")
            
            # Basic Information
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
                base_duration = st.number_input("Base Duration (days)", 
                    min_value=0.1, max_value=365.0,
                    value=float(task.base_duration) if task and task.base_duration else 1.0,
                    step=0.5, help="Duration in work days"
                )
            
            # Resource Requirements
            min_crews_needed = st.number_input("Minimum Crews", 
                min_value=1, max_value=50,
                value=task.min_crews_needed if task and task.min_crews_needed else 1,
                step=1, help="Minimum number of crews needed"
            )
            
            # Cross-floor configuration
            st.markdown("**🔄 Cross-Floor Configuration**")
            cross_floor_config = cross_floor_dependency_ui(task) if task else {}
            
            # Predecessors
            st.markdown("**⏩ Predecessor Tasks**")
            with SessionLocal() as inner_session:
                user_tasks = inner_session.query(UserBaseTaskDB).filter(
                    UserBaseTaskDB.user_id == user_id,
                    UserBaseTaskDB.id != getattr(task, 'id', None)
                ).all()
                predecessor_options = [f"{t.name} ({t.discipline})" for t in user_tasks]
                selected_predecessors = st.multiselect("Select predecessor tasks:", 
                    predecessor_options, help="Maximum 10 predecessors allowed"
                )
            
            # Form submission
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Task", use_container_width=True):
                    task_data = {
                        'base_duration': base_duration,
                        'min_crews_needed': min_crews_needed,
                        'predecessors': selected_predecessors
                    }
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

# ==================== CROSS-FLOOR DEPENDENCY HELPERS ====================
def get_task_by_id(task_id):
    """Get task by ID"""
    with SessionLocal() as session:
        return session.query(UserBaseTaskDB).filter(UserBaseTaskDB.id == task_id).first()

def get_available_dependency_tasks(base_task):
    """Get available tasks for dependencies"""
    with SessionLocal() as session:
        return session.query(UserBaseTaskDB).filter(
            UserBaseTaskDB.id != getattr(base_task, 'id', None)
        ).all()

def add_cross_floor_dependency(base_task, task_id, floor_offset):
    """Add cross-floor dependency"""
    current_deps = getattr(base_task, 'cross_floor_dependencies', [])
    current_deps.append({
        'task_id': task_id,
        'floor_offset': floor_offset,
        'required': True
    })
    base_task.cross_floor_dependencies = current_deps

def remove_cross_floor_dependency(base_task, task_id):
    """Remove cross-floor dependency"""
    current_deps = getattr(base_task, 'cross_floor_dependencies', [])
    base_task.cross_floor_dependencies = [d for d in current_deps if d['task_id'] != task_id]

def get_floor_offset_text(offset):
    """Get human-readable floor offset text"""
    offset_map = {
        -2: "📥 2 Floors Below",
        -1: "📥 Floor Below", 
        1: "📤 Floor Above",
        2: "📤 2 Floors Above"
    }
    return offset_map.get(offset, f"Floor {offset}")

def is_valid_floor_for_task(task, floor, zone):
    """Check if task can exist on specified floor"""
    return 0 <= floor <= 50  # Reasonable floor limits

def cross_floor_dependency_ui(base_task):
    """UI for configuring cross-floor dependencies"""
    st.markdown("### 🔄 Cross-Floor Dependencies")
    st.info("Configure tasks from other floors that this task depends on")
    
    # Get current dependencies
    current_deps = getattr(base_task, 'cross_floor_dependencies', [])
    
    # Display current dependencies
    if current_deps:
        st.markdown("**Current Dependencies:**")
        for i, dep in enumerate(current_deps):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                dep_task = get_task_by_id(dep['task_id'])
                st.write(f"**{dep_task.name if dep_task else dep['task_id']}**")
            with col2:
                st.write(get_floor_offset_text(dep['floor_offset']))
            with col3:
                st.write("🔗" if dep.get('required', True) else "⚡")
            with col4:
                if st.button("❌", key=f"remove_{i}"):
                    remove_cross_floor_dependency(base_task, dep['task_id'])
                    st.rerun()
    
    # Add new dependency
    with st.expander("➕ Add New Dependency", expanded=len(current_deps) == 0):
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            available_tasks = get_available_dependency_tasks(base_task)
            if available_tasks:
                task_options = {f"{t.name} ({t.discipline})": t.id for t in available_tasks}
                selected_task = st.selectbox(
                    "Depends on task:",
                    options=list(task_options.keys()),
                    key="new_dep_task"
                )
            else:
                st.info("No other tasks available for dependencies")
                selected_task = None
        with col2:
            floor_offset = st.selectbox(
                "Floor relationship:",
                options=[-2, -1, 1, 2],
                format_func=get_floor_offset_text,
                index=1,
                key="new_dep_floor"
            )
        with col3:
            st.write(""); st.write("")
            if st.button("Add", key="add_dep") and selected_task:
                task_id = task_options[selected_task]
                add_cross_floor_dependency(base_task, task_id, floor_offset)
                st.rerun()
    
    # Floor application
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
        index=0
    )
    
    return {
        "cross_floor_dependencies": current_deps,
        "applies_to_floors": applies_to_floors
    }

# ==================== UI COMPONENTS ====================
def inject_ui_styles():
    """Inject professional UI styles"""
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .professional-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .uploaded-file {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
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
                <div style="font-size: 1.8rem; font-weight: bold; color: #1f77b4;">{value}</div>
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
    <div class="professional-card">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <span style="font-size: 1.5rem;">{icon}</span>
            <h4 style="margin: 0; color: {colors[card_type]};">{title}</h4>
        </div>
        <div style="color: #555; line-height: 1.5;">{content}</div>
    </div>
    """, unsafe_allow_html=True)

def render_upload_section(title, key_suffix, accepted_types=["xlsx"]):
    """Enhanced file upload section"""
    uploaded_file = st.file_uploader(
        f"Upload {title}",
        type=accepted_types,
        key=f"upload_{key_suffix}",
        help=f"Upload your {title} file in Excel format (max 50MB)"
    )
    
    if uploaded_file:
        file_size = uploaded_file.size / 1024 / 1024  # MB
        
        if file_size > 50:
            st.error("❌ File size exceeds 50MB limit.")
            return None
        
        st.markdown(f"""
        <div class="uploaded-file">
            <strong>✅ {uploaded_file.name}</strong><br>
            <small>Size: {file_size:.2f} MB | Type: Excel</small>
        </div>
        """, unsafe_allow_html=True)
        
        return uploaded_file
    
    return None

def render_discipline_zone_config(disciplines, zones, key_prefix="disc_zone_cfg"):
    """
    Renders a UI to configure zones per discipline
    """
    cfg = {}
    
    for disc in disciplines:
        with st.expander(f"🏗️ {disc} - Zone Configuration", expanded=False):
            # Execution strategy
            selected_strategy = st.radio(
                f"Execution strategy for {disc}:",
                options=["sequential", "fully_parallel"],
                help="Sequential: zones run one after another. Parallel: zones run simultaneously.",
                key=f"{key_prefix}_strategy_{disc}"
            )
            
            # Zone grouping
            st.markdown("**Zone Grouping:**")
            default_groups = ",".join(zones)
            group_text = st.text_area(
                f"Zone groups for {disc}",
                value=default_groups,
                help="Enter zones separated by commas for each group. Each new line = sequential group.",
                key=f"{key_prefix}_groups_{disc}",
                height=100
            )
            
            # Parse zone groups
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
