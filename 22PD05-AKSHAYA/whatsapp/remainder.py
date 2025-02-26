import streamlit as st
import time
import threading
import schedule
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set page configuration
st.set_page_config(
    page_title="WhatsApp Remainder App",
    page_icon="📅",
    layout="wide"
)

# App title and description
st.title("📅 WhatsApp Remainder Automation")
st.markdown("Schedule automated remainders to be sent through WhatsApp Web")

# Initialize session state variables
if 'driver' not in st.session_state:
    st.session_state.driver = None
if 'remainders' not in st.session_state:
    st.session_state.remainders = []
if 'scheduler_running' not in st.session_state:
    st.session_state.scheduler_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'is_loaded' not in st.session_state:
    st.session_state.is_loaded = False
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

# Function to run the scheduler in a separate thread
def run_scheduler():
    while st.session_state.scheduler_running:
        schedule.run_pending()
        time.sleep(10)

# Function to send a remainder
def send_remainder(contact_name, message):
    try:
        log_message = f"[{datetime.now().strftime('%H:%M:%S')}] Sending remainder to {contact_name}..."
        st.session_state.logs.append(log_message)
        
        driver = st.session_state.driver
        if not driver:
            st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Driver not initialized. Please set up connection first.")
            return
        
        # Search for contact
        search_box = driver.find_element(By.XPATH, "//div[@contenteditable='true']")
        search_box.clear()
        search_box.send_keys(contact_name)
        time.sleep(2)
        search_box.send_keys(Keys.ENTER)

        time.sleep(2)  # Wait for chat to load

        # Send message
        message_box = driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")
        message_box.send_keys(message)
        message_box.send_keys(Keys.ENTER)
        
        st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Remainder sent to {contact_name} successfully!")
    except Exception as e:
        st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Error sending remainder: {str(e)}")

# Sidebar for setup
with st.sidebar:
    st.header("Setup")
    
    # Chrome settings
    st.subheader("Chrome Settings")
    user_data_dir = st.text_input("Chrome User Data Directory", value="C:\\Users\\YourUsername\\AppData\\Local\\Google\\Chrome\\User Data")
    profile_dir = st.text_input("Chrome Profile Directory", value="Default")
    chrome_driver_path = st.text_input("ChromeDriver Path", value="C:\\Program Files\\ChromeDriver\\chromedriver.exe")
    
    # Initialize and connect to WhatsApp Web
    if st.button("Initialize System"):
        with st.spinner("Setting up Chrome driver..."):
            try:
                # Setup Chrome options
                options = Options()
                options.add_argument(f"--user-data-dir={user_data_dir}")
                options.add_argument(f"--profile-directory={profile_dir}")
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                
                service = Service(chrome_driver_path)
                st.session_state.driver = webdriver.Chrome(service=service, options=options)
                st.session_state.is_loaded = True
                
                # Open WhatsApp Web
                st.session_state.driver.get("https://web.whatsapp.com")
                st.info("Opening WhatsApp Web. Please scan the QR code in the browser window.")
                st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] WhatsApp Web opened. Please scan QR code if needed.")
            except Exception as e:
                st.error(f"Error initializing system: {e}")
                st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Error initializing driver: {str(e)}")

# Main content
if st.session_state.is_loaded:
    # Check login status
    if not st.session_state.is_logged_in:
        if st.button("I've Scanned the QR Code"):
            time.sleep(5)  # Give extra time to load chats
            st.session_state.is_logged_in = True
            st.success("✅ WhatsApp Web logged in successfully!")
            st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully logged in to WhatsApp Web")
            st.rerun()
    
    # Remainder management interface
    if st.session_state.is_logged_in:
        # Create tabs for the main functionalities
        tabs = st.tabs(["Add Remainder", "View Remainders", "Logs"])
        
        # Tab 1: Add new remainder
        with tabs[0]:
            st.header("Schedule New Remainder")
            
            contact_name = st.text_input("Contact Name", help="Exact name as it appears in WhatsApp")
            remainder_message = st.text_area("Remainder Message", help="Message to be sent")
            remainder_time = st.text_input("Time (HH:MM in 24-hour format)", value="08:00", help="Time to send the remainder (24-hour format)")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Add Remainder", type="primary"):
                    if not contact_name or not remainder_message or not remainder_time:
                        st.error("Please fill in all fields")
                    else:
                        try:
                            # Validate time format
                            datetime.strptime(remainder_time, "%H:%M")
                            
                            # Create a new remainder
                            new_remainder = {
                                "id": len(st.session_state.remainders) + 1,
                                "contact": contact_name,
                                "message": remainder_message,
                                "time": remainder_time,
                                "active": True
                            }
                            
                            # Add to session state
                            st.session_state.remainders.append(new_remainder)
                            
                            # Schedule the remainder
                            schedule.every().day.at(remainder_time).do(
                                send_remainder, 
                                contact_name=contact_name, 
                                message=remainder_message
                            )
                            
                            st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Added remainder for {contact_name} at {remainder_time}")
                            st.success(f"✅ Remainder scheduled for {contact_name} at {remainder_time}")
                        except ValueError:
                            st.error("⚠️ Invalid time format. Please use HH:MM format (e.g., 08:30)")
            
            with col2:
                scheduler_status = "Running" if st.session_state.scheduler_running else "Stopped"
                st.write(f"Scheduler Status: {'🟢' if st.session_state.scheduler_running else '🔴'} {scheduler_status}")
                
                if st.session_state.scheduler_running:
                    if st.button("Stop Scheduler"):
                        st.session_state.scheduler_running = False
                        st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduler stopped")
                        st.success("✅ Scheduler stopped")
                        st.rerun()
                else:
                    if st.button("Start Scheduler"):
                        st.session_state.scheduler_running = True
                        threading.Thread(target=run_scheduler, daemon=True).start()
                        st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduler started")
                        st.success("✅ Scheduler started")
                        st.rerun()
        
        # Tab 2: View and manage remainders
        with tabs[1]:
            st.header("Manage Remainders")
            
            if not st.session_state.remainders:
                st.info("No remainders scheduled yet. Add one in the 'Add Remainder' tab.")
            else:
                # Display all remainders in a table
                remainder_data = []
                for remainder in st.session_state.remainders:
                    status = "🟢 Active" if remainder["active"] else "🔴 Inactive"
                    remainder_data.append([
                        remainder["id"],
                        remainder["contact"],
                        remainder["time"],
                        status,
                        remainder["message"][:20] + "..." if len(remainder["message"]) > 20 else remainder["message"]
                    ])
                
                st.dataframe(
                    remainder_data,
                    column_config={
                        0: "ID",
                        1: "Contact",
                        2: "Time",
                        3: "Status",
                        4: "Message Preview"
                    },
                    hide_index=True
                )
                
                # Remainder actions
                st.subheader("Remainder Actions")
                col1, col2 = st.columns(2)
                
                with col1:
                    remainder_id = st.number_input("Remainder ID", min_value=1, max_value=len(st.session_state.remainders), step=1)
                
                with col2:
                    action = st.selectbox("Action", ["View Details", "Toggle Active/Inactive", "Delete"])
                
                if st.button("Execute Action"):
                    if 1 <= remainder_id <= len(st.session_state.remainders):
                        idx = remainder_id - 1
                        
                        if action == "View Details":
                            remainder = st.session_state.remainders[idx]
                            st.json(remainder)
                        
                        elif action == "Toggle Active/Inactive":
                            st.session_state.remainders[idx]["active"] = not st.session_state.remainders[idx]["active"]
                            status = "activated" if st.session_state.remainders[idx]["active"] else "deactivated"
                            st.success(f"✅ Remainder {remainder_id} {status}")
                            st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Remainder {remainder_id} {status}")
                        
                        elif action == "Delete":
                            deleted = st.session_state.remainders.pop(idx)
                            st.success(f"✅ Remainder {remainder_id} deleted")
                            st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Deleted remainder for {deleted['contact']}")
                            
                            # Reindex remaining remainders
                            for i, rem in enumerate(st.session_state.remainders):
                                rem["id"] = i + 1
                    else:
                        st.error("⚠️ Invalid Remainder ID")
        
        # Tab 3: Logs
        with tabs[2]:
            st.header("Application Logs")
            
            # Add option to clear logs
            if st.button("Clear Logs"):
                st.session_state.logs = []
                st.success("✅ Logs cleared")
            
            # Display logs in reverse order (newest first)
            st.subheader("Log History")
            log_container = st.container(height=400)
            with log_container:
                for log in reversed(st.session_state.logs):
                    st.text(log)

# Add cleanup when app is closed
def cleanup():
    if st.session_state.driver:
        st.session_state.driver.quit()
        st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Browser closed")

# Register the cleanup function
import atexit
atexit.register(cleanup)

# Footer
st.markdown("---")
st.markdown("Created with Streamlit for WhatsApp Remainder Automation")