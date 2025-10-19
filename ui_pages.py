# ui_pages.py - FIXED VERSION
import streamlit as st
from backend.auth import auth_manager, require_role
from backend.database import SessionLocal
from backend.db_models import UserBaseTaskDB  # ✅ REMOVED BaseTaskDB - it doesn't exist
import pandas as pd
import os, time
from defaults import disciplines
# Import your existing UI logic
from scheduling_engin import run_schedule, analyze_project_progress
from ui_helpers import (
    inject_ui_styles, create_metric_row, create_info_card,
    render_upload_section, render_discipline_zone_config, 
    cross_floor_dependency_ui, constraint_manager,
    # Task management functions
    get_all_users, save_user_task, display_user_task_card,
    show_user_task_list, organize_tasks_by_discipline,
    user_specific_task_management, show_constrained_task_editor
)
from helpers import generate_quantity_template, generate_worker_template, generate_equipment_template, parse_quantity_excel, parse_worker_excel, parse_equipment_excel
from reporting import generate_interactive_gantt, MonitoringReporter  # ✅ ADDED MonitoringReporter
from defaults import workers, equipment, BASE_TASKS, disciplines

# ✅ FIXED: Initialize constraint manager properly
constraint_manager = SimpleConstraintManager()

# ------------------------- LOGIN / LOGOUT -------------------------
def login_ui():
    st.sidebar.title("🔐 User Login")
    
    if not auth_manager.is_authenticated():
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user = auth_manager.login(username, password)
            if user:
                st.session_state["user"] = user
                st.session_state["logged_in"] = True  # ✅ ADDED: Set login state
                st.success(f"Logged in as {user['username']} ({user['role']})")
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        user = auth_manager.get_current_user()
        st.sidebar.write(f"✅ Logged in: {user['username']} ({user['role']})")
        if st.sidebar.button("Logout"):
            auth_manager.logout()
            st.session_state.clear()
            st.rerun()

# ------------------------- PAGE WRAPPERS -------------------------
@require_role("admin", "manager")
def scheduling_page():
    generate_schedule_ui()

@require_role("admin", "manager", "worker", "viewer")
def monitoring_page():
    monitor_project_ui()

# ------------------------- MAIN PAGE ROUTER -------------------------
def main_ui():
    login_ui()

    if not st.session_state.get("logged_in", False):
        st.info("Please login to access project modules.")
        return

    user_role = st.session_state["user"]["role"]
    pages = {"Scheduling": scheduling_page, "Monitoring": monitoring_page}
    
    if user_role == "worker":
        pages.pop("Scheduling", None)

    st.sidebar.title("📂 Navigation")
    selection = st.sidebar.radio("Select Page", list(pages.keys()))

    page_func = pages.get(selection)
    if page_func:
        page_func()
    else:
        st.error("Page not available for your role.")

# ------------------------- ACTUAL UI FUNCTIONS -------------------------
def generate_schedule_ui():
    """Professional Construction Scheduler UI with user-editable tasks"""
    auth_manager.require_auth(access_level="write")

    inject_ui_styles()
    st.markdown('<div class="main-header">🏗️ Construction Project Scheduler Pro</div>', unsafe_allow_html=True)

    # Quick metrics
    if st.session_state.get("schedule_generated"):
        create_metric_row({
            "Zones Configured": f"{len(st.session_state.get('zones_floors', {}))}",
            "Tasks Processed": "Calculating...",
            "Schedule Duration": "Calculating...",
            "Files Generated": f"{len(st.session_state.get('generated_files', []))}"
        })

    # Main Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Project Setup", "📁 Templates", "📤 Upload Data", "🚀 Generate & Results", "📝 Manage Tasks"
    ])

    # ------------------ TAB 1: Project Setup ------------------
    with tab1:
        st.subheader("🏗️ Project Configuration")
        create_info_card("Project Setup Guide",
                         "Configure building zones, floors, and timeline. Each zone represents a distinct section.",
                         "🏗️", "info")

        with st.expander("🏢 Building Configuration", expanded=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                num_zones = st.number_input(
                    "How many zones does your building have?",
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
                    col1, col2, col3 = st.columns([3,1,1])
                    with col1:
                        zone_name = st.text_input("Zone name", value=f"Zone_{i + 1}", key=f"zone_name_{i}")
                    with col2:
                        max_floor = st.number_input("Floors", min_value=0, max_value=60, value=5, key=f"floor_{i}")
                    with col3:
                        st.metric("Floors", max_floor)
                    zones_floors[zone_name] = max_floor

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Project Start Date", value=pd.Timestamp.today(),
                                           help="Select the planned start date")
            with col2:
                st.metric("Start Date", start_date.strftime("%Y-%m-%d"))

        with st.expander("🏢 Zones Sequencing", expanded=True):
            st.subheader("⚙️ Discipline-Zone Configuration")
            st.markdown("Define which zones should be executed in parallel and which sequentially per discipline.")
            discipline_zone_cfg = render_discipline_zone_config(disciplines, list(zones_floors.keys()))
            st.session_state["discipline_zone_cfg"] = discipline_zone_cfg
        
        with st.expander("📝 Project Information", expanded=False):
            project_name = st.text_input("Project Name", value="My Construction Project")
            project_manager = st.text_input("Project Manager")
            if project_name and project_manager:
                st.success(f"✅ Project '{project_name}' configured with manager {project_manager}")

        st.session_state["zones_floors"] = zones_floors
        st.session_state["start_date"] = start_date

    # ------------------ TAB 2: Templates ------------------
    with tab2:
        st.subheader("📊 Generate Data Templates")
        create_info_card("Template Instructions",
                         "Download these templates, fill with your project data, then upload in next tab.",
                         "📋","info")
        col1, col2, col3 = st.columns(3)
        with col1: create_info_card("Quantity Template","Task quantities per zone/floor","📏","info")
        with col2: create_info_card("Worker Template","Crew sizes and productivity rates","👷","info")
        with col3: create_info_card("Equipment Template","Machine counts and rates","🚜","info")

        if st.button("🎯 Generate All Templates"):
            try:
                with st.spinner("🔄 Preparing professional templates..."):
                    zones_floors = st.session_state.get("zones_floors", {})
                    if not zones_floors:
                        st.error("❌ Please configure zones and floors in Project Setup first")
                        st.stop()
                    
                    # ✅ FIXED: Use UserBaseTaskDB instead of BaseTaskDB
                    current_user_id = st.session_state["user"].get("id", 1)  # Default to user_id=1
                    with SessionLocal() as session:
                        user_tasks = session.query(UserBaseTaskDB).filter(
                            UserBaseTaskDB.user_id == current_user_id,
                            UserBaseTaskDB.included == True
                        ).all()
                        
                        if not user_tasks:
                            st.warning("⚠️ No user tasks found. Using default tasks.")
                            tasks_dict = BASE_TASKS
                        else:
                            tasks_dict = organize_tasks_by_discipline(user_tasks)
                    
                    # Generate templates with USER tasks
                    qty_file = generate_quantity_template(tasks_dict, zones_floors)
                    worker_file = generate_worker_template(workers)
                    equip_file = generate_equipment_template(equipment)

                    st.session_state.update({
                        "templates_ready": True,
                        "qty_file": qty_file,
                        "worker_file": worker_file,
                        "equip_file": equip_file,
                        "user_tasks_used": len(user_tasks) > 0
                    })
                    st.success("✅ All templates generated successfully!")
                    if st.session_state.get("user_tasks_used"):
                        st.info("📋 Templates generated using your modified task library")
                    st.balloons()
                    
            except Exception as e:
                st.error(f"❌ Failed to generate templates: {e}")
                import traceback
                st.code(traceback.format_exc())
    
        if st.session_state.get("templates_ready", False):
            st.markdown("---")
            st.subheader("⬇️ Download Templates")

            templates_info = [ ("📏 Quantity Template", "qty_file", "Defines task quantities across zones/floors"),
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
                                st.download_button("Download", f,
                                                   file_name=os.path.basename(path_or_buf),
                                                   use_container_width=True,
                                                   key=f"download_{key}")
                        elif hasattr(path_or_buf, "getvalue"):
                            st.download_button("Download", data=path_or_buf.getvalue(),
                                               file_name=f"{key.replace('_file', '')}.xlsx",
                                               use_container_width=True,
                                               key=f"download_{key}")

    # ------------------ TAB 3: Upload ------------------
    with tab3:
        st.subheader("📤 Upload Your Project Data")
        create_info_card("Upload Requirements",
                         "Upload all three filled templates to proceed with schedule generation.",
                         "📤","info")
        quantity_file = render_upload_section("Quantity Matrix", "quantity")
        worker_file = render_upload_section("Worker Template", "worker") 
        equipment_file = render_upload_section("Equipment Template", "equipment")

        upload_status = { "Quantity Matrix": bool(quantity_file),
                          "Worker Template": bool(worker_file),
                          "Equipment Template": bool(equipment_file)}
        st.markdown("### 📊 Upload Status")
        status_cols = st.columns(3)
        for idx, (name, status) in enumerate(upload_status.items()):
            with status_cols[idx]:
                st.success(f"✅ {name}") if status else st.warning(f"⏳ {name}")

    # ------------------ TAB 4: Generate & Results ------------------
    with tab4:
        st.subheader("🚀 Generate Project Schedule")
        all_ready = all([quantity_file, worker_file, equipment_file])
        
        if all_ready:
            # Enhanced Configuration Summary
            with st.expander("📋 Configuration Summary", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    zones_count = len(st.session_state.get("zones_floors", {}))
                    st.metric("Zones", zones_count)
                
                with col2:
                    total_floors = sum(st.session_state.get("zones_floors", {}).values())
                    st.metric("Total Floors", total_floors)
                
                with col3:
                    # ✅ FIXED: Use UserBaseTaskDB
                    current_user_id = st.session_state["user"].get("id", 1)
                    with SessionLocal() as session:
                        task_count = session.query(UserBaseTaskDB).filter(
                            UserBaseTaskDB.user_id == current_user_id,
                            UserBaseTaskDB.included == True
                        ).count()
                    st.metric("Tasks", task_count)
                
                with col4:
                    st.metric("User", st.session_state["user"]["username"])
                
                # Show task source information
                with SessionLocal() as session:
                    user_modified_tasks = session.query(UserBaseTaskDB).filter(
                        UserBaseTaskDB.user_id == current_user_id,
                        UserBaseTaskDB.included == True,
                        UserBaseTaskDB.created_by_user == True
                    ).count()
                
                if user_modified_tasks > 0:
                    st.success(f"🎯 Using {user_modified_tasks} user-modified tasks")
                else:
                    st.info("🔧 Using default task library")

            create_info_card("Ready to Generate", "Click below to generate the schedule using your configuration.", "✅", "success")
            
            # FIXED: Enhanced schedule generation with user tasks
            if st.button("🚀 Generate Optimized Schedule"):
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    steps = [
                        "📊 Parsing Excel files...", "🔍 Validating data...", "🏗️ Loading user task configuration...",
                        "🔄 Generating tasks with hybrid dependencies...", "📈 Generating reports...", "🎉 Finalizing output..."
                    ]
                    
                    # Variables to store parsed data
                    quantity_used, workers_used, equipment_used = None, None, None
                    
                    for i, step in enumerate(steps):
                        status_text.subheader(step)
                        progress_bar.progress((i+1)*16)
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
                            # ✅ FIXED: Use UserBaseTaskDB
                            current_user_id = st.session_state["user"].get("id", 1)
                            with SessionLocal() as session:
                                user_tasks = session.query(UserBaseTaskDB).filter(
                                    UserBaseTaskDB.user_id == current_user_id,
                                    UserBaseTaskDB.included == True
                                ).all()
                                
                                if user_tasks:
                                    user_tasks_dict = organize_tasks_by_discipline(user_tasks)
                                    st.info(f"📋 Using {len(user_tasks)} user-configured tasks")
                                else:
                                    user_tasks_dict = None
                                    st.info("🔧 Using default task library")
                            
                            # Generate schedule with user tasks
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
                    
                    if st.session_state.get("user_tasks_used"):
                        status_text.subheader("✅ Schedule Generated with Your Custom Tasks!")
                    else:
                        status_text.subheader("✅ Schedule Generated Successfully!")
                    
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Schedule generation failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            missing = [n for n, s in upload_status.items() if not s]
            create_info_card("Action Required", f"Upload files: {', '.join(missing)}", "⚠️", "warning")
            
        if st.session_state.get("schedule_generated", False):
            st.markdown("---")
            st.subheader("📂 Download Results")
            
            # Excel files
            excel_files = [f for f in st.session_state["generated_files"] if f.endswith(".xlsx")]
            if excel_files:
                st.markdown("#### 📊 Excel Reports")
                cols = st.columns(3)
                for i, file_path in enumerate(excel_files):
                    if os.path.exists(file_path):
                        with cols[i % 3]:
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

    # ------------------ TAB 5: Manage Tasks ------------------
    with tab5:
        user_specific_task_management(
def monitor_project_ui():
    """
    Streamlit UI for project monitoring. Only runs analysis when both files are present.
    """
    auth_manager.require_auth(access_level="read")
    st.header("📊 Project Monitoring (S-Curve & Deviation)")
    st.markdown(
        "Upload a **Reference Schedule** (Excel with a 'Schedule' sheet containing Start/End) "
        "and an **Actual Progress** file (Date, Progress). Analysis runs only when both are uploaded."
    )

    reference_file = st.file_uploader("Upload Reference Schedule Excel (.xlsx)", type=["xlsx"], key="ref_schedule")
    actual_file = st.file_uploader("Upload Actual Progress Excel (.xlsx)", type=["xlsx"], key="actual_progress")

    with st.expander("Help: expected formats / sample rows"):
        st.markdown("""
        **Reference schedule** — must contain `Start` and `End` columns (dates).  
        **Actual progress** — should contain `Date` and `Progress` (0-1 or 0-100).  
        """)

    if reference_file and not actual_file:
        try:
            ref_df = pd.read_excel(reference_file, sheet_name="Schedule")
            st.subheader("Reference schedule preview")
            st.dataframe(ref_df.head(200))
            st.info("Upload an 'Actual Progress' file to perform monitoring analysis.")
        except Exception as e:
            st.error(f"Unable to read reference schedule: {e}")
        return

    if reference_file and actual_file:
        try:
            ref_df = pd.read_excel(reference_file, sheet_name="Schedule")
            act_df = pd.read_excel(actual_file)
            if "Progress" in act_df.columns and act_df["Progress"].max() > 1.1:
                act_df["Progress"] /= 100.0
            from reporting import MonitoringReporter
            reporter = MonitoringReporter(ref_df, act_df)
            reporter.compute_analysis()
            analysis_df = getattr(reporter, "analysis_df", analyze_project_progress(ref_df, act_df))

            import plotly.express as px
            st.subheader("📈 S-Curve (Planned vs Actual cumulative progress)")
            fig_s = px.line(analysis_df, x="Date", y=["PlannedProgress", "CumulativeActual"],
                            labels={"value": "Cumulative Progress", "variable": "Series"},
                            title="S-Curve: Planned vs Actual")
            st.plotly_chart(fig_s, use_container_width=True)

            st.subheader("📊 Deviation (Actual - Planned)")
            fig_dev = px.area(analysis_df, x="Date", y="ProgressDeviation", title="Progress Deviation")
            st.plotly_chart(fig_dev, use_container_width=True)

            csv_bytes = analysis_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download analysis CSV", csv_bytes, file_name="monitoring_analysis.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Monitoring analysis failed: {e}")
            import traceback
            st.code(traceback.format_exc())
        return

    if not reference_file and not actual_file:
        st.info("Upload files to start monitoring. For schedule generation use the Generate Schedule tab.")

# ------------------------- RUN -------------------------
if __name__ == "__main__":
    main_ui()
