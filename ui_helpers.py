import streamlit as st

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
            if file_size > 50:
                st.error("❌ File size exceeds 50MB limit.")
                return None
            
            return uploaded_file  # ✅ CRITICAL: Return the file object
        
        return None
