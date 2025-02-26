import streamlit as st
import subprocess
import os
import sys
from PIL import Image
import base64
import time

# Set page configuration
st.set_page_config(
    page_title="WhatsApp Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def run_script(script_path):
    try:
        # Check if the script exists
        if not os.path.exists(script_path):
            st.error(f"Script not found: {script_path}")
            return False
            
        # Display debug information
        st.info(f"Attempting to launch: {script_path}")
        
        # Run the script with Streamlit in a new process
        process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give the process a moment to start
        time.sleep(1)
        
        # Check if process is still running
        if process.poll() is None:
            st.success(f"Launched {os.path.basename(script_path)} successfully!")
            
            # Add a link to open in a new tab (using the default Streamlit port)
            st.markdown(f"If it doesn't open automatically, [click here](http://localhost:8501) to open in a new tab.")
            return True
        else:
            # Get error output if process failed
            _, stderr = process.communicate()
            if stderr:
                st.error(f"Error in script: {stderr}")
            else:
                st.error(f"Script execution failed for unknown reason")
            return False
            
    except Exception as e:
        st.error(f"Error launching {script_path}: {e}")
        return False

# Function to get base64 encoded image
def get_base64_encoded_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None

# CSS to enhance the UI
st.markdown("""
<style>
    .main-container {
        background-color: #f5f5f5;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .feature-button {
        background-color: #25D366;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
        margin: 10px 0;
        width: 100%;
        transition: background-color 0.3s;
    }
    .feature-button:hover {
        background-color: #128C7E;
    }
    .feature-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .app-title {
        color: #128C7E;
        text-align: center;
        margin-bottom: 30px;
    }
    .feature-description {
        color: #333;
        margin-bottom: 15px;
    }
    .stButton>button {
        background-color: #25D366;
        color: white;
        font-weight: bold;
        border: none;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #128C7E;
    }
</style>
""", unsafe_allow_html=True)

# App header with WhatsApp-inspired design
st.markdown("<h1 class='app-title'>WhatsApp Assistant Hub</h1>", unsafe_allow_html=True)

# Try to load and display WhatsApp logo
try:
    # Attempt to display a local WhatsApp logo if available
    logo_path = "whatsapp_logo.png"  # Update this path to your logo
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo, width=150)
except Exception:
    # If logo loading fails, continue without an image
    pass

st.markdown("<div class='main-container'>", unsafe_allow_html=True)
st.markdown("### Welcome to your WhatsApp Assistant")
st.markdown("Select a feature to get started:")
st.markdown("</div>", unsafe_allow_html=True)

# Normalize paths for cross-platform compatibility
base_dir = "P:\\aks\\pages\\whatsapp"  # Keep your original base path
# Alternative: Use current directory as base
# base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whatsapp")

# Define script paths
summarize_path = os.path.join(base_dir, "summarize.py")
autoresponse_path = os.path.join(base_dir, "automate_respone.py")  # Note the typo in original
reminder_path = os.path.join(base_dir, "remainder.py")

# Create three columns for the features
col1, col2, col3 = st.columns(3)

# Store launch status
if 'launch_status' not in st.session_state:
    st.session_state.launch_status = {
        'summarize': False,
        'autoresponse': False,
        'reminder': False
    }

with col1:
    st.markdown("<div class='feature-card'>", unsafe_allow_html=True)
    st.markdown("#### 💬 Chat Summarizer")
    st.markdown("<p class='feature-description'>Extract and summarize your WhatsApp conversations to quickly understand the key points of lengthy chats.</p>", unsafe_allow_html=True)
    
    # Show either launch button or status
    if not st.session_state.launch_status['summarize']:
        if st.button("Launch Summarizer", key="summarize_btn", help="Launch the WhatsApp Chat Summarizer"):
            st.session_state.launch_status['summarize'] = run_script(summarize_path)
    else:
        st.success("Summarizer is running")
        if st.button("Stop Summarizer", key="stop_summarize"):
            st.session_state.launch_status['summarize'] = False
            st.experimental_rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='feature-card'>", unsafe_allow_html=True)
    st.markdown("#### 🤖 Auto Response")
    st.markdown("<p class='feature-description'>Set up automated responses for your WhatsApp messages when you're busy or unavailable.</p>", unsafe_allow_html=True)
    
    if not st.session_state.launch_status['autoresponse']:
        if st.button("Launch Auto Response", key="autoresponse_btn", help="Launch the WhatsApp Auto Response System"):
            st.session_state.launch_status['autoresponse'] = run_script(autoresponse_path)
    else:
        st.success("Auto Response is running")
        if st.button("Stop Auto Response", key="stop_autoresponse"):
            st.session_state.launch_status['autoresponse'] = False
            st.experimental_rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div class='feature-card'>", unsafe_allow_html=True)
    st.markdown("#### ⏰ Reminders")
    st.markdown("<p class='feature-description'>Schedule and manage WhatsApp reminders to never miss important messages or events.</p>", unsafe_allow_html=True)
    
    if not st.session_state.launch_status['reminder']:
        if st.button("Launch Reminders", key="reminder_btn", help="Launch the WhatsApp Reminder System"):
            st.session_state.launch_status['reminder'] = run_script(reminder_path)
    else:
        st.success("Reminders is running")
        if st.button("Stop Reminders", key="stop_reminder"):
            st.session_state.launch_status['reminder'] = False
            st.experimental_rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)

# Additional information
st.markdown("<div class='main-container'>", unsafe_allow_html=True)
st.markdown("### How to Use")
st.markdown("""
1. Click on one of the feature buttons above to launch the corresponding tool
2. Each tool will open in a new window or browser tab
3. You can return to this main menu at any time to access other features
4. If a tool fails to launch, check the system status section below
""")
st.markdown("</div>", unsafe_allow_html=True)

# System status information
st.markdown("<div class='main-container'>", unsafe_allow_html=True)
st.markdown("### System Status")

# Check if required scripts exist
required_scripts = [summarize_path, autoresponse_path, reminder_path]
status_col1, status_col2 = st.columns(2)

with status_col1:
    st.markdown("#### Required Files:")
    for script in required_scripts:
        script_exists = os.path.exists(script)
        status = "✅ Found" if script_exists else "❌ Missing"
        st.markdown(f"- {os.path.basename(script)}: {status}")

with status_col2:
    # Display Python and Streamlit versions
    st.markdown("#### Environment:")
    python_version = sys.version.split()[0]
    st.markdown(f"- Python Version: {python_version}")
    try:
        import streamlit
        streamlit_version = streamlit.__version__
        st.markdown(f"- Streamlit Version: {streamlit_version}")
    except:
        st.markdown("- Streamlit Version: Unknown")

    # Check if streamlit is in PATH
    try:
        streamlit_path = subprocess.check_output([sys.executable, "-m", "pip", "show", "streamlit"]).decode()
        st.markdown("- Streamlit: Installed")
    except:
        st.markdown("- Streamlit: Not found in PATH")

st.markdown("</div>", unsafe_allow_html=True)

# Path configuration (allow customization)
with st.expander("Configure Paths"):
    st.markdown("If your scripts are in a different location, you can specify the paths here:")
    custom_base_dir = st.text_input("Base Directory", value=base_dir)
    if custom_base_dir != base_dir:
        base_dir = custom_base_dir
        summarize_path = os.path.join(base_dir, "summarize.py")
        autoresponse_path = os.path.join(base_dir, "automate_respone.py")
        reminder_path = os.path.join(base_dir, "remainder.py")
        st.success("Paths updated!")

# Footer
st.markdown("---")
st.markdown("WhatsApp Assistant Hub | Created with Streamlit")