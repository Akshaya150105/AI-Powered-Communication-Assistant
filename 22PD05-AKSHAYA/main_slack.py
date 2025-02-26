import streamlit as st
import subprocess
import os
import webbrowser
import time
import sys
from datetime import datetime

def main():
    # Set page configuration
    st.set_page_config(
        page_title="Slack Communication Optimizer",
        page_icon="💬",
        layout="wide"
    )
    
    # Custom CSS to improve appearance
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #4A154B;
            margin-bottom: 0;
        }
        .sub-header {
            font-size: 1.2rem;
            color: #454245;
            margin-top: 0;
            margin-bottom: 2rem;
        }
        .card {
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            background-color: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card-title {
            font-weight: bold;
            color: #4A154B;
            font-size: 1.3rem;
        }
        .card-description {
            color: #454245;
            margin-top: 10px;
            margin-bottom: 15px;
        }
        .stButton>button {
            background-color: #4A154B;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #611f69;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create sidebar
    with st.sidebar:
        st.image("https://cdn.cdnlogo.com/logos/s/40/slack-new.svg", width=120)
        st.markdown("### Workspace")
        workspaces = ["Team Alpha", "Marketing", "Engineering", "Sales"]
        selected_workspace = st.selectbox("Select Workspace", workspaces)
        
        st.markdown("### Time Range")
        date_range = st.date_input(
            "Date Range",
            [datetime.now().date(), datetime.now().date()]
        )
        
        st.markdown("### Channels")
        channels = ["#general", "#random", "#announcements", "#project-x", "#help"]
        selected_channels = st.multiselect("Select Channels", channels, default=["#general"])
        
        st.markdown("---")
        if st.button("Connect to Slack", key="connect"):
            st.success("Connected to Slack successfully!")
    
    # Main content
    st.markdown('<h1 class="main-header">Slack Communication Optimizer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Transform your team communication with AI-powered insights</p>', unsafe_allow_html=True)
    
    # Statistics cards in a row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
            <div class="card" style="text-align: center;">
                <div style="font-size: 2rem;">152</div>
                <div>Messages Today</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class="card" style="text-align: center;">
                <div style="font-size: 2rem;">7</div>
                <div>Active Channels</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class="card" style="text-align: center;">
                <div style="font-size: 2rem;">23</div>
                <div>Action Items</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
            <div class="card" style="text-align: center;">
                <div style="font-size: 2rem;">85%</div>
                <div>Response Rate</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("## What would you like to do today?")
    
    # Define app paths
    app_paths = {
        "Summarize": "P:\\aks\\pages\\slack\\pages\\summarize.py",
        "Convert to Tasks": "P:\\aks\\pages\\slack\\pages\\convert_tasks.py",
        "Daily Digest": "P:\\aks\\pages\\slack\\pages\\daily_digest.py",
        "Search Retrieval": "P:\\aks\\pages\\slack\\pages\\search_retrieval.py"
    }
    
    # Initialize the app_launched session state if not exists
    if 'app_launched' not in st.session_state:
        st.session_state.app_launched = {app: False for app in app_paths.keys()}
    
    # Feature cards in two rows with buttons that launch separate apps
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div class="card">
                <div class="card-title">Summarize Key Conversations</div>
                <div class="card-description">Get AI-generated summaries of important channel discussions, decisions, and action items.</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Summarize", key="summarize"):
            # Reset launch flag for other apps
            for app in app_paths.keys():
                if app != "Summarize":
                    st.session_state.app_launched[app] = False
            launch_app(app_paths["Summarize"], "Summarize")
            
        st.markdown("""
            <div class="card">
                <div class="card-title">Convert Messages to Tasks</div>
                <div class="card-description">Automatically extract action items from conversations and add them to your task manager.</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Convert to Tasks", key="convert_tasks"):
            # Reset launch flag for other apps
            for app in app_paths.keys():
                if app != "Convert to Tasks":
                    st.session_state.app_launched[app] = False
            launch_app(app_paths["Convert to Tasks"], "Convert to Tasks")
    
    with col2:
        st.markdown("""
            <div class="card">
                <div class="card-title">Daily Digests</div>
                <div class="card-description">Receive an organized summary of all important updates across all your channels.</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Daily Digest", key="daily_digest"):
            # Reset launch flag for other apps
            for app in app_paths.keys():
                if app != "Daily Digest":
                    st.session_state.app_launched[app] = False
            launch_app(app_paths["Daily Digest"], "Daily Digest")
            
        st.markdown("""
            <div class="card">
                <div class="card-title">Smart Search & Retrieval</div>
                <div class="card-description">Find exactly what you need with semantic search across all your Slack history.</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Search Retrieval", key="search_retrieval"):
            # Reset launch flag for other apps
            for app in app_paths.keys():
                if app != "Search Retrieval":
                    st.session_state.app_launched[app] = False
            launch_app(app_paths["Search Retrieval"], "Search Retrieval")
    
    # Status indicator
    st.markdown("---")
    if 'status' in st.session_state and st.session_state.status:
        st.info(st.session_state.status)
    
    
def launch_app(app_path, app_name):
    """Launch a separate Streamlit application in a new process"""
    if not os.path.exists(app_path):
        st.session_state["status"] = f"⚠️ Error: Could not find {app_name} at {app_path}"
        return

    # Check if this app has already been launched 
    if st.session_state.app_launched.get(app_name, False):
        st.session_state["status"] = f"ℹ️ {app_name} is already running"
        return
    
    # Set the launch flag for this app
    st.session_state.app_launched[app_name] = True
    
    # Set status
    st.session_state["status"] = f"Launching {app_name}..."

    # Start the Streamlit process on a different port
    port = get_available_port(8501)
    subprocess.Popen(f"streamlit run {app_path} --server.port {port}", shell=True)

    # Give the app a moment to start
    time.sleep(2)

    # Open the browser to the app
    webbrowser.open(f"http://localhost:{port}")

    # Update status
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