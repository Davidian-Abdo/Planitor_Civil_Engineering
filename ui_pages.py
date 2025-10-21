
import streamlit as st
import pandas as pd
import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

# Backend imports
from backend.auth import auth_manager, require_role
from backend.database import SessionLocal
from backend.db_models import UserBaseTaskDB
from backend.init_backend import check_backend_health

# Core application imports
from scheduling_engine import run_schedule, analyze_project_progress
from ui_helpers import (
    inject_ui_styles, create_metric_row, create_info_card,
    render_upload_section, render_discipline_zone_config, 
    enhanced_task_management, organize_tasks_by_discipline
)
from helpers import (
    generate_quantity_template, generate_worker_template, 
    generate_equipment_template, parse_quantity_excel, 
    parse_worker_excel, parse_equipment_excel
)
from reporting import generate_interactive_gantt, MonitoringReporter
from defaults import workers, equipment, BASE_TASKS, disciplines

class UIConfig:
    """Configuration constants for UI elements"""
    TAB_ICONS = {
        "project_setup": "📋",
        "templates": "📁", 
        "upload": "📤",
        "generate": "🚀",
        "tasks": "📝"
    }
    
    ROLE_PAGES = {
        "admin": ["Scheduling", "Monitoring", "Task Management"],
        "manager": ["Scheduling", "Monitoring", "Task Management"],
        "worker": ["Monitoring"],
        "viewer": ["Monitoring"]
    }


class SessionStateManager:
    """Manage session state with validation and defaults"""
    
    @staticmethod
    def initialize_session_state():
        """Initialize all required session state variables"""
        defaults = {
            "logged_in": False,
            "user": None,
            "zones_floors": {},
            "start_date": pd.Timestamp.today().date(),
            "templates_ready": False,
            "schedule_generated": False,
            "discipline_zone_cfg": {},
            "generated_files": [],
            "output_folder": "",
            "user_tasks_used": False
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def validate_session_state() -> bool:
        """Validate that required session state is present"""
        required = ["logged_in", "user"]
        return all(key in st.session_state for key in required)


class DatabaseHelper:
    """Database operations helper for UI"""
    
    @staticmethod
    def get_user_tasks(user_id: int) -> List[UserBaseTaskDB]:
        """Get tasks for a specific user"""
        try:
            with SessionLocal() as session:
                return session.query(UserBaseTaskDB).filter(
                    UserBaseTaskDB.user_id == user_id,
                    UserBaseTaskDB.included == True
                ).all()
        except Exception as e:
            st.error(f"❌ Failed to load user tasks: {e}")
            return []

    @staticmethod
    def get_user_modified_tasks_count(user_id: int) -> int:
        """Count how many tasks user has modified"""
        try:
            with SessionLocal() as session:
                return session.query(UserBaseTaskDB).filter(
                    UserBaseTaskDB.user_id == user_id,
                    UserBaseTaskDB.included == True,
                    UserBaseTaskDB.created_by_user == True
                ).count()
        except Exception:
            return 0


class TemplateManager:
    """Manage template generation and download"""
    
    @staticmethod
    def generate_all_templates(zones_floors: Dict, user_id: int) -> bool:
        """Generate all required templates"""
        try:
            with st.spinner("🔄 Preparing professional templates..."):
                if not zones_floors:
                    st.error("❌ Please configure zones and floors in Project Setup first")
                    return False
                
                # Get user tasks or fallback to defaults
                user_tasks = DatabaseHelper.get_user_tasks(user_id)
                
                if not user_tasks:
                    st.warning("⚠️ No user tasks found. Using default tasks.")
                    tasks_dict = BASE_TASKS
                else:
                    tasks_dict = organize_tasks_by_discipline(user_tasks)
                
                # Generate templates
                qty_file = generate_quantity_template(tasks_dict, zones_floors)
                worker_file = generate_worker_template(workers)
                equip_file = generate_equipment_template(equipment)

                # Update session state
                st.session_state.update({
                    "templates_ready": True,
                    "qty_file": qty_file,
                    "worker_file": worker_file,
                    "equip_file": equip_file,
                    "user_tasks_used": len(user_tasks) > 0
                })
                
                return True
                
        except Exception as e:
            st.error(f"❌ Failed to generate templates: {e}")
            return False

    @staticmethod
    def render_download_section():
        """Render template download section"""
        if not st.session_state.get("templates_ready"):
            return
            
        st.markdown("---")
        st.subheader("⬇️ Download Templates")

        templates_info = [
            ("📏 Quantity Template", "qty_file", "Defines task quantities across zones/floors"),
            ("👷 Worker Template", "worker_file", "Specifies crew sizes and productivity rates"), 
            ("🚜 Equipment Template", "equip_file", "Details machine counts and operational rates")
        ]
        
        for icon, key, description in templates_info:
            path_or_buf = st.session_state.get(key)
            if not path_or_buf:
                continue

            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{icon} {description}**")
                with col2:
                    if isinstance(path_or_buf, str) and os.path.exists(path_or_buf):
                        with open(path_or_buf, "rb") as f:
                            st.download_button(
                                "Download", f,
                                file_name=os.path.basename(path_or_buf),
                                use_container_width=True,
                                key=f"download_{key}"
                            )
                    elif hasattr(path_or_buf, "getvalue"):
                        st.download_button(
                            "Download", 
                            data=path_or_buf.getvalue(),
                            file_name=f"{key.replace('_file', '')}.xlsx",
                            use_container_width=True,
                            key=f"download_{key}"
                        )


class ScheduleGenerator:
    """Handle schedule generation process"""
    
    @staticmethod
    def generate_schedule(quantity_file, worker_file, equipment_file, user_id: int):
        """Generate optimized schedule"""
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            steps = [
                "📊 Parsing Excel files...", 
                "🔍 Validating data...", 
                "🏗️ Loading user task configuration...",
                "🔄 Generating tasks with hybrid dependencies...", 
                "📈 Generating reports...", 
                "🎉 Finalizing output..."
            ]
            
            # Variables to store parsed data
            quantity_used, workers_used, equipment_used = None, None, None
            user_tasks_dict = None
            
            for i, step in enumerate(steps):
                status_text.subheader(step)
                progress_bar.progress((i + 1) * 16)
                time.sleep(0.3)
                
                if i == 0:
                    df_quantity = pd.read_excel(quantity_file)
                    quantity_used = parse_quantity_excel(df_quantity)
                    
                elif i == 1:
                    df_worker = pd.read_excel(worker_file)
                    workers_used = parse_worker_excel(df_worker)
                    
                elif i == 2:
                    df_equip = pd.read_excel(equipment_file)
                    equipment_used = parse_equipment_excel(df_equip)
                    
                elif i == 3:
                    # Load user tasks
                    user_tasks = DatabaseHelper.get_user_tasks(user_id)
                    user_tasks_dict = organize_tasks_by_discipline(user_tasks) if user_tasks else None
                    
                    if user_tasks_dict:
                        st.info(f"📋 Using {len(user_tasks)} user-configured tasks")
                    else:
                        st.info("🔧 Using default task library")
                    
                    # Generate schedule
                    schedule, output_folder = run_schedule(
                        zone_floors=st.session_state.get("zones_floors", {}),
                        quantity_matrix=quantity_used,
                        start_date=st.session_state.get("start_date"),
                        workers_dict=workers_used,
                        equipment_dict=equipment_used,
                        discipline_zone_cfg=st.session_state.get("discipline_zone_cfg"),
                        base_tasks_override=user_tasks_dict
                    )
                    
                elif i == 4:
                    st.session_state.update({
                        "schedule_generated": True,
                        "output_folder": output_folder,
                        "generated_files": [os.path.join(output_folder, f) for f in os.listdir(output_folder)],
                        "user_tasks_used": user_tasks_dict is not None
                    })
                    
                    # Generate interactive Gantt chart
                    schedule_excel_path = os.path.join(output_folder, "construction_schedule_optimized.xlsx")
                    if os.path.exists(schedule_excel_path):
                        gantt_html = os.path.join(output_folder, "interactive_gantt.html")
                        generate_interactive_gantt(pd.read_excel(schedule_excel_path), gantt_html)
                        st.session_state["generated_files"].append(gantt_html)
            
            progress_bar.progress(100)
            return True
            
        except Exception as e:
            st.error(f"❌ Schedule generation failed: {e}")
            return False

    @staticmethod
    def render_results_section():
        """Render schedule results download section"""
        if not st.session_state.get("schedule_generated"):
            return
            
        st.markdown("---")
        st.subheader("📂 Download Results")
        
        # Excel files
        excel_files = [f for f in st.session_state["generated_files"] if f.endswith(".xlsx")]
        if excel_files:
            st.markdown("#### 📊 Excel Reports")
            cols = st.columns(min(3, len(excel_files)))
            for i, file_path in enumerate(excel_files):
                if os.path.exists(file_path):
                    with cols[i % len(cols)]:
                        with open(file_path, "rb") as f:
                            st.download_button(
                                f"📥 {os.path.basename(file_path)}",
                                f,
                                file_name=os.path.basename(file_path),
                                use_container_width=True,
                                key=f"excel_download_{i}"
                            )
        
        # Gantt chart
        gantt_files = [f for f in st.session_state["generated_files"] if f.endswith(".html")]
        if gantt_files:
            st.markdown("#### 📈 Interactive Gantt Chart")
            gantt_file = gantt_files[0]
            if os.path.exists(gantt_file):
                with open(gantt_file, "rb") as f:
                    st.download_button(
                        "📊 Download Interactive Gantt Chart",
                        f,
                        file_name="project_gantt_chart.html",
                        use_container_width=True,
                        type="secondary",
                        key="gantt_download"
                    )


# ------------------------- AUTHENTICATION -------------------------
def login_ui():
    """Render login UI in sidebar"""
    st.sidebar.title("🔐 User Login")
    
    if not auth_manager.is_authenticated():
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        
        if st.sidebar.button("Login", use_container_width=True):
            user = auth_manager.login(username, password)
            if user:
                st.session_state.update({
                    "user": user,
                    "logged_in": True
                })
                st.success(f"✅ Logged in as {user['username']} ({user['role']})")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
    else:
        user = auth_manager.get_current_user()
        st.sidebar.success(f"✅ {user['username']} ({user['role']})")
        if st.sidebar.button("Logout", use_container_width=True):
            auth_manager.logout()
            st.session_state.clear()
            st.rerun()


# ------------------------- PAGE ROUTERS -------------------------
@require_role("admin", "manager")
def scheduling_page():
    """Scheduling page with role-based access"""
    generate_schedule_ui()


@require_role("admin", "manager", "worker", "viewer") 
def monitoring_page():
    """Monitoring page with role-based access"""
    monitor_project_ui()


def main_ui():
    """Main UI router"""
    # Initialize session state
    SessionStateManager.initialize_session_state()
    
    # Render login UI
    login_ui()

    # Check authentication
    if not st.session_state.get("logged_in"):
        st.info("🔐 Please login to access project modules.")
        return

    # Check backend health
    health_status = check_backend_health()
    if not health_status.get("overall_healthy", False):
        st.error("🚨 Backend system is not healthy. Please check server logs.")
        return

    # Navigation based on user role
    user_role = st.session_state["user"]["role"]
    available_pages = UIConfig.ROLE_PAGES.get(user_role, [])
    
    if not available_pages:
        st.error("❌ No pages available for your role.")
        return

    st.sidebar.title("📂 Navigation")
    selection = st.sidebar.radio("Select Page", available_pages)

    # Route to selected page
    page_map = {
        "Scheduling": scheduling_page,
        "Monitoring": monitoring_page,
        "Task Management": lambda: enhanced_task_management()
    }
    
    page_func = page_map.get(selection)
    if page_func:
        page_func()
    else:
        st.error("❌ Page not implemented yet.")


# ------------------------- MAIN UI PAGES -------------------------
def generate_schedule_ui():
    """Professional Construction Scheduler UI"""
    auth_manager.require_auth(access_level="write")
    
    # Inject custom styles
    inject_ui_styles()
    
    # Header
    st.markdown('<div class="main-header">🏗️ Construction Project Scheduler Pro</div>', unsafe_allow_html=True)

    # Quick metrics
    if st.session_state.get("schedule_generated"):
        create_metric_row({
            "Zones Configured": f"{len(st.session_state.get('zones_floors', {}))}",
            "Tasks Processed": "Calculating...",
            "Schedule Duration": "Calculating...", 
            "Files Generated": f"{len(st.session_state.get('generated_files', []))}"
        })

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"{UIConfig.TAB_ICONS['project_setup']} Project Setup",
        f"{UIConfig.TAB_ICONS['templates']} Templates", 
        f"{UIConfig.TAB_ICONS['upload']} Upload Data",
        f"{UIConfig.TAB_ICONS['generate']} Generate & Results",
        f"{UIConfig.TAB_ICONS['tasks']} Manage Tasks"
    ])

    with tab1:
        render_project_setup_tab()
        
    with tab2:
        render_templates_tab()
        
    with tab3:
        render_upload_tab()
        
    with tab4:
        render_generate_tab()
        
    with tab5:
        enhanced_task_management()


def render_project_setup_tab():
    """Render project setup tab"""
    st.subheader("🏗️ Project Configuration")
    create_info_card(
        "Project Setup Guide",
        "Configure building zones, floors, and timeline. Each zone represents a distinct section.",
        "🏗️", "info"
    )

    # Building Configuration
    with st.expander("🏢 Building Configuration", expanded=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            num_zones = st.number_input(
                "Number of building zones:",
                min_value=1, max_value=30, value=2,
                help="Each zone represents a distinct section of the building",
                key="num_zones_input"
            )
        with col2:
            st.metric("Zones Configured", num_zones)

        zones_floors = {}
        st.markdown("### Zone Details")
        
        for i in range(num_zones):
            with st.container():
                st.markdown(f"**Zone {i + 1}**")
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    zone_name = st.text_input("Zone name", value=f"Zone_{i + 1}", key=f"zone_name_{i}")
                with col2:
                    max_floor = st.number_input("Floors", min_value=0, max_value=60, value=5, key=f"floor_{i}")
                with col3:
                    st.metric("Floors", max_floor)
                zones_floors[zone_name] = max_floor

        # Project timeline
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Project Start Date", 
                value=pd.Timestamp.today().date(),
                help="Select the planned start date"
            )
        with col2:
            st.metric("Start Date", start_date.strftime("%Y-%m-%d"))

    # Zones Sequencing
    with st.expander("🏢 Zones Sequencing", expanded=True):
        st.subheader("⚙️ Discipline-Zone Configuration")
        st.markdown("Define which zones should be executed in parallel and which sequentially per discipline.")
        discipline_zone_cfg = render_discipline_zone_config(disciplines, list(zones_floors.keys()))
        st.session_state["discipline_zone_cfg"] = discipline_zone_cfg

    # Project Information
    with st.expander("📝 Project Information", expanded=False):
        project_name = st.text_input("Project Name", value="My Construction Project")
        project_manager = st.text_input("Project Manager")
        
        if project_name and project_manager:
            st.success(f"✅ Project '{project_name}' configured with manager {project_manager}")

    # Update session state
    st.session_state.update({
        "zones_floors": zones_floors,
        "start_date": start_date
    })


def render_templates_tab():
    """Render templates tab"""
    st.subheader("📊 Generate Data Templates")
    create_info_card(
        "Template Instructions",
        "Download these templates, fill with your project data, then upload in next tab.",
        "📋", "info"
    )
    
    # Template overview
    col1, col2, col3 = st.columns(3)
    with col1: 
        create_info_card("Quantity Template", "Task quantities per zone/floor", "📏", "info")
    with col2: 
        create_info_card("Worker Template", "Crew sizes and productivity rates", "👷", "info")
    with col3: 
        create_info_card("Equipment Template", "Machine counts and rates", "🚜", "info")

    # Generate templates button
    if st.button("🎯 Generate All Templates", use_container_width=True):
        user_id = st.session_state["user"].get("id", 1)
        if TemplateManager.generate_all_templates(st.session_state["zones_floors"], user_id):
            st.success("✅ All templates generated successfully!")
            if st.session_state.get("user_tasks_used"):
                st.info("📋 Templates generated using your modified task library")
            st.balloons()

    # Download section
    TemplateManager.render_download_section()


def render_upload_tab():
    """Render upload tab"""
    st.subheader("📤 Upload Your Project Data")
    create_info_card(
        "Upload Requirements", 
        "Upload all three filled templates to proceed with schedule generation.",
        "📤", "info"
    )
    
    # File upload sections
    quantity_file = render_upload_section("Quantity Matrix", "quantity")
    worker_file = render_upload_section("Worker Template", "worker")
    equipment_file = render_upload_section("Equipment Template", "equipment")

    # Upload status
    upload_status = {
        "Quantity Matrix": bool(quantity_file),
        "Worker Template": bool(worker_file), 
        "Equipment Template": bool(equipment_file)
    }
    
    st.markdown("### 📊 Upload Status")
    status_cols = st.columns(3)
    for idx, (name, status) in enumerate(upload_status.items()):
        with status_cols[idx]:
            if status:
                st.success(f"✅ {name}")
            else:
                st.warning(f"⏳ {name}")


def render_generate_tab():
    """Render generate and results tab"""
    st.subheader("🚀 Generate Project Schedule")
    
    # Get uploaded files from session state
    quantity_file = st.session_state.get("quantity_file")
    worker_file = st.session_state.get("worker_file") 
    equipment_file = st.session_state.get("equipment_file")
    
    all_ready = all([quantity_file, worker_file, equipment_file])
    
    if all_ready:
        render_configuration_summary()
        
        create_info_card(
            "Ready to Generate", 
            "Click below to generate the schedule using your configuration.", 
            "✅", "success"
        )
        
        # Generate schedule button
        if st.button("🚀 Generate Optimized Schedule", use_container_width=True, type="primary"):
            user_id = st.session_state["user"].get("id", 1)
            if ScheduleGenerator.generate_schedule(quantity_file, worker_file, equipment_file, user_id):
                if st.session_state.get("user_tasks_used"):
                    st.success("✅ Schedule Generated with Your Custom Tasks!")
                else:
                    st.success("✅ Schedule Generated Successfully!")
                st.balloons()
    else:
        missing = [name for name, status in {
            "Quantity Matrix": not quantity_file,
            "Worker Template": not worker_file,
            "Equipment Template": not equipment_file
        }.items() if status]
        
        create_info_card(
            "Action Required", 
            f"Upload files: {', '.join(missing)}", 
            "⚠️", "warning"
        )
    
    # Results section
    ScheduleGenerator.render_results_section()


def render_configuration_summary():
    """Render configuration summary"""
    with st.expander("📋 Configuration Summary", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            zones_count = len(st.session_state.get("zones_floors", {}))
            st.metric("Zones", zones_count)
        
        with col2:
            total_floors = sum(st.session_state.get("zones_floors", {}).values())
            st.metric("Total Floors", total_floors)
        
        with col3:
            user_id = st.session_state["user"].get("id", 1)
            user_tasks = DatabaseHelper.get_user_tasks(user_id)
            task_count = len(user_tasks) if user_tasks else len([task for tasks in BASE_TASKS.values() for task in tasks])
            st.metric("Tasks", task_count)
        
        with col4:
            st.metric("User", st.session_state["user"]["username"])
        
        # Task source information
        user_id = st.session_state["user"].get("id", 1)
        user_modified_count = DatabaseHelper.get_user_modified_tasks_count(user_id)
        
        if user_modified_count > 0:
            st.success(f"🎯 Using {user_modified_count} user-modified tasks")
        else:
            st.info("🔧 Using default task library")


def monitor_project_ui():
    """
    Streamlit UI for project monitoring with S-Curve analysis
    """
    auth_manager.require_auth(access_level="read")
    
    st.header("📊 Project Monitoring (S-Curve & Deviation)")
    st.markdown(
        "Upload a **Reference Schedule** and an **Actual Progress** file to analyze project performance."
    )

    # File uploaders
    reference_file = st.file_uploader("Upload Reference Schedule Excel (.xlsx)", type=["xlsx"], key="ref_schedule")
    actual_file = st.file_uploader("Upload Actual Progress Excel (.xlsx)", type=["xlsx"], key="actual_progress")

    # Help section
    with st.expander("📋 Expected File Formats", expanded=False):
        st.markdown("""
        **Reference Schedule** (Excel):
        - Must contain 'Schedule' sheet with 'Start' and 'End' date columns
        
        **Actual Progress** (Excel):  
        - Should contain 'Date' and 'Progress' columns
        - Progress can be 0-1 or 0-100 (automatically normalized)
        """)

    # Handle file processing
    if reference_file and actual_file:
        process_monitoring_files(reference_file, actual_file)
    elif reference_file and not actual_file:
        preview_reference_file(reference_file)
    elif not reference_file and not actual_file:
        st.info("📁 Upload both files to start monitoring analysis.")


def process_monitoring_files(reference_file, actual_file):
    """Process monitoring files and generate analysis"""
    try:
        # Read and validate files
        ref_df = pd.read_excel(reference_file, sheet_name="Schedule")
        act_df = pd.read_excel(actual_file)
        
        # Normalize progress if needed
        if "Progress" in act_df.columns and act_df["Progress"].max() > 1.1:
            act_df["Progress"] /= 100.0
        
        # Perform analysis
        reporter = MonitoringReporter(ref_df, act_df)
        reporter.compute_analysis()
        analysis_df = getattr(reporter, "analysis_df", analyze_project_progress(ref_df, act_df))

        # Display results
        render_monitoring_charts(analysis_df)
        
        # Download option
        csv_bytes = analysis_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Analysis CSV", 
            csv_bytes, 
            file_name="monitoring_analysis.csv", 
            mime="text/csv",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"❌ Monitoring analysis failed: {e}")
        st.code(f"Error details: {str(e)}")


def preview_reference_file(reference_file):
    """Preview reference file when only one file is uploaded"""
    try:
        ref_df = pd.read_excel(reference_file, sheet_name="Schedule")
        st.subheader("📋 Reference Schedule Preview")
        st.dataframe(ref_df.head(200))
        st.info("📤 Upload an 'Actual Progress' file to perform monitoring analysis.")
    except Exception as e:
        st.error(f"❌ Unable to read reference schedule: {e}")


def render_monitoring_charts(analysis_df):
    """Render monitoring charts"""
    import plotly.express as px
    
    # S-Curve
    st.subheader("📈 S-Curve (Planned vs Actual Progress)")
    fig_s = px.line(
        analysis_df, 
        x="Date", 
        y=["PlannedProgress", "CumulativeActual"],
        labels={"value": "Cumulative Progress", "variable": "Series"},
        title="S-Curve: Planned vs Actual Progress"
    )
    st.plotly_chart(fig_s, use_container_width=True)

    # Deviation chart
    st.subheader("📊 Progress Deviation")
    fig_dev = px.area(
        analysis_df, 
        x="Date", 
        y="ProgressDeviation", 
        title="Progress Deviation (Actual - Planned)"
    )
    st.plotly_chart(fig_dev, use_container_width=True)


# ------------------------- APPLICATION ENTRY POINT -------------------------
if __name__ == "__main__":
    main_ui()
