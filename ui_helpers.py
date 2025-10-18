import streamlit as st
from defaults import disciplines
from models import DisciplineZoneConfig


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
