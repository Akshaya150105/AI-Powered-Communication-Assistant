import streamlit as st
import subprocess
import os
import webbrowser
import time

def main():
    # Page configuration
    st.set_page_config(
        page_title="Email Management System",
        page_icon="📧",
        layout="centered"
    )
    
    # Header
    st.title("📧 Email Management Dashboard")
    st.markdown("#### Select an action to launch the appropriate tool")
    
    
    app_paths = {
        "Flag Email": "P:\\aks\\pages\\gmail\\flag_email.py",
        "Summarize Email": "P:\\aks\\pages\\gmail\\summarize.py",
        "Prioritize Incoming Emails": "P:\\aks\\pages\\gmail\\priortize.py",
        "Suggest Quick Responses": "P:\\aks\\pages\\gmail\\quick_responses.py"
    }
    
    # Create columns for buttons
    col1, col2 = st.columns(2)
    
    # Create buttons with icons
    with col1:
        if st.button("🚩 Flag Email", use_container_width=True):
            launch_app(app_paths["Flag Email"], "Flag Email")
            
        if st.button("🔍 Summarize Email", use_container_width=True):
            launch_app(app_paths["Summarize Email"], "Summarize Email")
            
    with col2:
        if st.button("⭐ Prioritize Incoming Emails", use_container_width=True):
            launch_app(app_paths["Prioritize Incoming Emails"], "Prioritize Incoming Emails")
            
        if st.button("💬 Suggest Quick Responses", use_container_width=True):
            launch_app(app_paths["Suggest Quick Responses"], "Suggest Quick Responses")
    
    # Status and help information
    st.markdown("---")
    if 'status' in st.session_state and st.session_state.status:
        st.info(st.session_state.status)
    
    with st.expander("ℹ️ How to use this dashboard"):
        st.write("""
        1. Click on any button to launch the corresponding email management tool
        2. Each tool will open in a new browser tab
        3. You can return to this dashboard at any time by closing the tab
        4. Make sure all your Streamlit app files are in the correct locations specified in the configuration
        """)

def launch_app(app_path, app_name):
    """Launch a separate Streamlit application in a new process"""
    if not os.path.exists(app_path):
        st.session_state["status"] = f"⚠️ Error: Could not find {app_name} at {app_path}"
        return
    
    # Prevent duplicate status updates
    if st.session_state.get("status", "") == f"✅ {app_name} launched successfully!":
        return  

    # Set status once
    st.session_state["status"] = f"Launching {app_name}..."
    
    # Start the Streamlit process on a different port
    port = get_available_port(8501)
    subprocess.Popen(f"streamlit run {app_path} --server.port {port}", shell=True)

    # Give the app a moment to start
    time.sleep(2)
    
    # Open the browser to the app
    webbrowser.open(f"http://localhost:{port}")
    
    # Update status once
    st.session_state["status"] = f"✅ {app_name} launched successfully!"


def get_available_port(start_port):
    """Find an available port starting from the given port number"""
    port = start_port
    # Simple implementation - in practice you might want to check if ports are in use
    return port + hash(time.time()) % 1000  # Just to get a somewhat random port

if __name__ == "__main__":
    # Initialize session state if not exists
    if 'status' not in st.session_state:
        st.session_state.status = ""
    
    main()