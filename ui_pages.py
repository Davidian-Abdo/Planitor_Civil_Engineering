# ui_pages.py
import streamlit as st
from backend.auth import auth_manager, require_role, login, logout  # Updated imports
from backend.database import SessionLocal
from backend.db_models import BaseTaskDB
import pandas as pd
import os, time

# Import your existing UI logic (keep these the same)
from scheduling_engin import run_schedule, analyze_project_progress
from ui_helpers import inject_ui_styles, create_metric_row, create_info_card, render_upload_section
from helpers import generate_quantity_template, generate_worker_template, generate_equipment_template,parse_quantity_excel, parse_worker_excel, parse_equipment_excel
from reporting import  generate_interactive_gantt
from defaults import workers,eauipment, BASE_TASKS

# ------------------------- LOGIN / LOGOUT -------------------------
def login_ui():
    st.sidebar.title("🔐 User Login")
    
    # Use auth_manager for state checking
    if not auth_manager.is_authenticated():
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user = auth_manager.login(username, password)  # Use auth_manager directly
            if user:
                st.session_state["user"] = user  # Keep for compatibility
                st.success(f"Logged in as {user['username']} ({user['role']})")
                st.rerun()  # Use rerun() instead of experimental_rerun()
            else:
                st.error("Invalid credentials")
    else:
        user = auth_manager.get_current_user()  # Get validated user
        st.sidebar.write(f"✅ Logged in: {user['username']} ({user['role']})")
        if st.sidebar.button("Logout"):
            auth_manager.logout()
            st.session_state.clear()
            st.rerun()

# ------------------------- PAGE WRAPPERS -------------------------
@require_role("admin", "manager")
def scheduling_page():
    generate_schedule_ui()

@require_role("admin", "manager", "worker", "viewer")  # Added viewer role
def monitoring_page():
    monitor_project_ui()


# ------------------------- MAIN PAGE ROUTER -------------------------
def main_ui():
    login_ui()  # Sidebar login/logout

    if not st.session_state.get("logged_in", False):
        st.info("Please login to access project modules.")
        return

    # Sidebar navigation
    user_role = st.session_state["user"]["role"]
    pages = {"Scheduling": scheduling_page, "Monitoring": monitoring_page}
    # Optionally hide pages based on role
    if user_role == "worker":
        pages.pop("Scheduling", None)

    st.sidebar.title("📂 Navigation")
    selection = st.sidebar.radio("Select Page", list(pages.keys()))

    # Call selected page
    page_func = pages.get(selection)
    if page_func:
        page_func()
    else:
        st.error("Page not available for your role.")

# ------------------------- ACTUAL UI FUNCTIONS -------------------------
def generate_schedule_ui():
    """Professional Construction Scheduler UI with user-editable tasks"""
    auth_manager.require_auth(access_level="write")  # ✅ add the parameter name
    


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
        "📋 Project Setup",
        "📁 Templates",
        "📤 Upload Data",
        "🚀 Generate & Results",
        "📝 Manage Tasks"
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
                    with SessionLocal() as session:
                        base_tasks = session.query(BaseTaskDB).filter(BaseTaskDB.included==True).all()
                        tasks_dict = {t.name: t for t in base_tasks}

                    qty_file = generate_quantity_template(BASE_TASKS, st.session_state.get("zones_floors", {}))
                    worker_file = generate_worker_template(workers)
                    equip_file = generate_equipment_template(equipment)

                    st.session_state.update({
                        "templates_ready": True,
                        "qty_file": qty_file,
                        "worker_file": worker_file,
                        "equip_file": equip_file
                    })
                    st.success("✅ All templates generated successfully!")
                    st.balloons()
                    
            except Exception as e:
                st.error(f"❌ Failed to generate templates: {e}")

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
            create_info_card("Ready to Generate","Click below to generate the schedule.","✅","success")
            if st.button("🚀 Generate Optimized Schedule"):
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    steps = ["📊 Parsing Excel files...",
                             "🔍 Validating data...",
                             "🏗️ Running schedule engine...",
                             "📈 Generating reports...",
                             "🎉 Finalizing output..."]
                    for i, step in enumerate(steps):
                        status_text.subheader(step)
                        progress_bar.progress((i+1)*20)
                        time.sleep(0.3)
                        if i==0:
                            df_quantity = pd.read_excel(quantity_file)
                            quantity_used = parse_quantity_excel(df_quantity)
                        elif i==1:
                            df_worker = pd.read_excel(worker_file)
                            workers_used = parse_worker_excel(df_worker)
                        elif i==2:
                            df_equip = pd.read_excel(equipment_file)
                            equipment_used = parse_equipment_excel(df_equip)
                        elif i==3:
                            schedule, output_folder = run_schedule(
                                zone_floors=st.session_state.get("zones_floors", {}),
                                quantity_matrix=quantity_used,
                                start_date=st.session_state.get("start_date"),
                                workers_dict=workers_used,
                                equipment_dict=equipment_used
                            )
                        elif i==4:
                            st.session_state.update({
                                "schedule_generated": True,
                                "output_folder": output_folder,
                                "generated_files": [os.path.join(output_folder,f) for f in os.listdir(output_folder)]
                            })
                            schedule_excel_path = os.path.join(output_folder,"construction_schedule_optimized.xlsx")
                            if os.path.exists(schedule_excel_path):
                                gantt_html = os.path.join(output_folder,"interactive_gantt.html")
                                generate_interactive_gantt(pd.read_excel(schedule_excel_path), gantt_html)
                                st.session_state["generated_files"].append(gantt_html)
                    progress_bar.progress(100)
                    status_text.subheader("✅ Schedule Generated Successfully!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Schedule generation failed: {e}")
        else:
            missing = [n for n,s in upload_status.items() if not s]
            create_info_card("Action Required", f"Upload files: {', '.join(missing)}","⚠️","warning")

    # ------------------ TAB 5: Manage Tasks ------------------
    with tab5:
        st.subheader("📝 Manage Base Tasks")
        st.markdown("Add, edit, or delete tasks used in scheduling.")

        with SessionLocal() as session:
            tasks = session.query(BaseTaskDB).order_by(BaseTaskDB.id).all()

        for t in tasks:
            cols = st.columns([4,2,1])
            with cols[0]:
                st.markdown(f"**{t.name}** | {t.discipline} | Type: {t.resource_type} | {t.base_duration}d")
            with cols[1]:
                if st.button("✏️ Edit", key=f"edit_{t.id}"):
                    st.session_state["edit_task_id"] = t.id
            with cols[2]:
                if st.button("❌ Delete", key=f"delete_{t.id}"):
                    try:
                        with SessionLocal() as session:
                            task_to_delete = session.query(BaseTaskDB).get(t.id)
                            if task_to_delete:
                                session.delete(task_to_delete)
                                session.commit()
                                st.success(f"Deleted '{t.name}'")
                                st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

        # Add/Edit Task Form
        task_to_edit = None
        if st.session_state.get("edit_task_id"):
            with SessionLocal() as session:
                task_to_edit = session.query(BaseTaskDB).get(st.session_state["edit_task_id"])

        with st.expander("➕ Add / Edit Task", expanded=True):
            with st.form("task_form"):
                task_name = st.text_input("Task Name", value=(task_to_edit.name if task_to_edit else ""))
                disciplines = ["Préliminaire","Terrassement","Fondations","Structure","VRD","Finitions"]
                resource_types = ["worker","equipment","hybrid"]
                discipline = st.selectbox("Discipline", disciplines,
                                          index=disciplines.index(task_to_edit.discipline) if task_to_edit else 0)
                resource_type = st.selectbox("Resource Type", resource_types,
                                             index=resource_types.index(task_to_edit.resource_type) if task_to_edit else 0)
                base_duration = st.number_input("Base Duration (days)", min_value=0.1, step=0.1,
                                                value=(task_to_edit.base_duration if task_to_edit else 1.0))
                min_crews_needed = st.number_input("Minimum Crews", min_value=1, step=1,
                                                  value=(task_to_edit.min_crews_needed if task_to_edit else 1))
                repeat_on_floor = st.checkbox("Repeat per Floor?", value=(task_to_edit.repeat_on_floor if task_to_edit else True))
                included = st.checkbox("Include in Schedule?", value=(task_to_edit.included if task_to_edit else True))
                submitted = st.form_submit_button("💾 Save Task")

                if submitted:
                    if not task_name.strip():
                        st.error("Task name cannot be empty")
                    else:
                        try:
                            with SessionLocal() as session:
                                if task_to_edit:
                                    task_to_edit.name = task_name
                                    task_to_edit.discipline = discipline
                                    task_to_edit.resource_type = resource_type
                                    task_to_edit.base_duration = base_duration
                                    task_to_edit.min_crews_needed = min_crews_needed
                                    task_to_edit.repeat_on_floor = repeat_on_floor
                                    task_to_edit.included = included
                                    session.add(task_to_edit)
                                    session.commit()
                                    st.success(f"Updated '{task_name}'")
                                    st.session_state.pop("edit_task_id")
                                else:
                                    new_task = BaseTaskDB(
                                        name=task_name,
                                        discipline=discipline,
                                        resource_type=resource_type,
                                        base_duration=base_duration,
                                        min_crews_needed=min_crews_needed,
                                        repeat_on_floor=repeat_on_floor,
                                        included=included,
                                        created_by_user=True
                                    )
                                    session.add(new_task)
                                    session.commit()
                                    st.success(f"Added '{task_name}'")
                                st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Save failed: {e}")

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
