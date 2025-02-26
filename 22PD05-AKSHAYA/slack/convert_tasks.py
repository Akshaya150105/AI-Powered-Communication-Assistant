import streamlit as st
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import spacy
import dateparser
import re
import time
from datetime import datetime, timedelta
st.set_page_config(
    page_title="Slack Task Extractor", 
    page_icon="🔍", 
    layout="wide",
    initial_sidebar_state="expanded"
)

SLACK_BOT_TOKEN = "xoxb-8497485985891-8494927306197-YWinmCEXrlbf2oz2N7I9TLw3"
client = WebClient(token=SLACK_BOT_TOKEN)

# Load English NLP Model
@st.cache_resource
def load_nlp_model():
    return spacy.load("en_core_web_sm")

nlp = load_nlp_model()

# Custom CSS
st.markdown(
    """
    <style>
        .stApp { 
            background-color: #f8f9fa;
        }
        .main-title {
            color: #4A154B;
            text-align: center;
            font-size: 42px;
            font-weight: bold;
            margin-bottom: 10px;
            padding-top: 20px;
        }
        .sub-title {
            color: #616061;
            text-align: center;
            font-size: 20px;
            margin-bottom: 30px;
        }
        .task-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 15px;
            border-left: 5px solid #4A154B;
        }
        .task-priority-high {
            border-left: 5px solid #E01E5A;
        }
        .task-priority-medium {
            border-left: 5px solid #ECB22E;
        }
        .task-priority-low {
            border-left: 5px solid #2EB67D;
        }
        .metric-card {
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #4A154B;
        }
        .metric-label {
            font-size: 14px;
            color: #616061;
        }
        .section-header {
            color: #4A154B;
            font-weight: bold;
            margin-top: 30px;
            margin-bottom: 20px;
            padding-bottom: 5px;
            border-bottom: 2px solid #4A154B;
        }
        .slack-button {
            background-color: #4A154B;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            padding: 10px 20px;
            border: none;
            transition: all 0.3s;
        }
        .slack-button:hover {
            background-color: #611f69;
            cursor: pointer;
        }
        .hover-zoom:hover {
            transform: scale(1.02);
            transition: transform 0.2s;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state for tracking tasks
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'history' not in st.session_state:
    st.session_state.history = []
if 'assigned_users' not in st.session_state:
    st.session_state.assigned_users = {}

st.markdown('<p class="main-title">🔍 Slack Task Extractor</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Discover, organize, and assign tasks from your Slack conversations</p>', unsafe_allow_html=True)

st.sidebar.image("https://cdn.cdnlogo.com/logos/s/40/slack-new.svg", width=50)
st.sidebar.title("⚙️ Configuration")
try:
    channels_response = client.conversations_list()
    channels = {channel["name"]: channel["id"] for channel in channels_response["channels"]}
    channel_name = st.sidebar.selectbox("🔖 Choose a Slack Channel", list(channels.keys()))
    channel_id = channels[channel_name]
except Exception as e:
    st.sidebar.error(f"⚠️ Error fetching channels: {e}")
    channels = {}
    channel_id = None
with st.sidebar.expander("🛠️ Advanced Options", expanded=False):
    message_limit = st.slider("Number of messages to analyze", min_value=10, max_value=1000, value=100, step=10)
    
    time_options = {
        "Last 24 hours": 1,
        "Last 3 days": 3,
        "Last week": 7,
        "Last month": 30,
        "All time": None
    }
    time_frame = st.selectbox("Time frame", list(time_options.keys()))
    
    default_keywords = "fix, update, create, send, invite, submit, deploy, check, review, rename, complete, implement, write, prepare, organize, schedule"
    task_keywords_input = st.text_area("Task keywords (comma separated)", value=default_keywords)
    task_keywords = {keyword.strip() for keyword in task_keywords_input.split(",")}

def analyze_task_message(message):
    """Extract task information and estimate priority from a message."""
    
    if len(message.split()) > 30:
        return None
    
    urgency_indicators = {
        "high": ["urgent", "asap", "immediately", "today", "critical", "important", "high priority", "ASAP", "emergency"],
        "medium": ["soon", "next week", "tomorrow", "needed", "should", "medium priority"],
        "low": ["when possible", "sometime", "low priority", "maybe", "consider", "think about"]
    }
    
    # Tokenize message
    doc = nlp(message.lower())
    
    # Check if a verb is in task_keywords
    task_verb = None
    for token in doc:
        if token.pos_ == "VERB" and token.lemma_ in task_keywords:
            task_verb = token.lemma_
            break
    
    if not task_verb:
        return None
    
    priority = "medium"  
    
    for level, indicators in urgency_indicators.items():
        if any(indicator in message.lower() for indicator in indicators):
            priority = level
            break
    
    due_date = None
    date_patterns = ["by tomorrow", "by next week", "by Monday", "by Tuesday", "by Wednesday", 
                     "by Thursday", "by Friday", "by Saturday", "by Sunday", "by today",
                     "due tomorrow", "due next week", "due on"]
    
    for pattern in date_patterns:
        if pattern in message.lower():
            date_text = message.lower().split(pattern)[1].strip().split()[0]
            parsed_date = dateparser.parse(date_text)
            if parsed_date:
                due_date = parsed_date.strftime("%Y-%m-%d")
                break
    
    mentioned_users = []
    for entity in doc.ents:
        if entity.label_ == "PERSON":
            mentioned_users.append(entity.text)
    
    return {
        "task": message, 
        "action": task_verb, 
        "priority": priority,
        "due_date": due_date,
        "assignee": mentioned_users[0] if mentioned_users else "Unassigned"
    }

# Main Content Area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<h2 class="section-header">📋 Task Dashboard</h2>', unsafe_allow_html=True)
    
    
    if st.button("🔍 Extract Tasks", key="extract_button"):
        with st.spinner("Analyzing Slack conversations..."):
            try:
                
                oldest_timestamp = None
                if time_options[time_frame]:
                    days = time_options[time_frame]
                    oldest_date = datetime.now() - timedelta(days=days)
                    oldest_timestamp = oldest_date.timestamp()
                
                # Fetch messages
                response = client.conversations_history(
                    channel=channel_id, 
                    limit=message_limit,
                    oldest=oldest_timestamp
                )
                
                # Process messages
                messages = [
                    msg["text"].strip()
                    for msg in response["messages"]
                    if "text" in msg
                    and "user" in msg
                    and not msg.get("bot_id")
                    and "joined the channel" not in msg["text"].lower()
                ]
                
                # Clear previous tasks
                st.session_state.tasks = []
                
                # Extract tasks
                for message in messages:
                    task_info = analyze_task_message(message)
                    if task_info:
                        st.session_state.tasks.append(task_info)
                
                # Store in history
                if st.session_state.tasks:
                    st.session_state.history.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "channel": channel_name,
                        "task_count": len(st.session_state.tasks)
                    })
                
                time.sleep(0.5) 
                st.success(f"Found {len(st.session_state.tasks)} tasks in #{channel_name}")
                
            except SlackApiError as e:
                st.error(f"Error fetching messages: {e.response['error']}")

    # Display metrics
    if st.session_state.tasks:
        metrics_cols = st.columns(4)
        
        with metrics_cols[0]:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value">{len(st.session_state.tasks)}</div>
                    <div class="metric-label">Total Tasks</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with metrics_cols[1]:
            high_priority = sum(1 for task in st.session_state.tasks if task["priority"] == "high")
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value" style="color: #E01E5A;">{high_priority}</div>
                    <div class="metric-label">High Priority</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with metrics_cols[2]:
            medium_priority = sum(1 for task in st.session_state.tasks if task["priority"] == "medium")
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value" style="color: #ECB22E;">{medium_priority}</div>
                    <div class="metric-label">Medium Priority</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with metrics_cols[3]:
            low_priority = sum(1 for task in st.session_state.tasks if task["priority"] == "low")
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value" style="color: #2EB67D;">{low_priority}</div>
                    <div class="metric-label">Low Priority</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Display tasks
        st.markdown("### 📝 Extracted Tasks")
        
        # Filter options
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            priority_filter = st.multiselect(
                "Filter by Priority", 
                options=["high", "medium", "low"],
                default=["high", "medium", "low"]
            )
        
        with filter_col2:
            sort_option = st.selectbox(
                "Sort by", 
                options=["Priority (High to Low)", "Priority (Low to High)"]
            )
        
        # Sort tasks
        sorted_tasks = sorted(
            [task for task in st.session_state.tasks if task["priority"] in priority_filter],
            key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]],
            reverse=(sort_option == "Priority (Low to High)")
        )
        
        # Display each task
        for i, task in enumerate(sorted_tasks, 1):
            priority_class = f"task-priority-{task['priority']}"
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[task["priority"]]
            
            st.markdown(
                f"""
                <div class="task-card {priority_class} hover-zoom">
                    <h3>{priority_emoji} Task {i}</h3>
                    <p><strong>Description:</strong> {task['task']}</p>
                    <p><strong>Action Type:</strong> {task['action'].capitalize()}</p>
                    <p><strong>Assignee:</strong> {task['assignee']}</p>
                    <p><strong>Priority:</strong> {task['priority'].capitalize()}</p>
                    {f"<p><strong>Due Date:</strong> {task['due_date']}</p>" if task['due_date'] else ""}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Send to Slack Button
        if st.button("📤 Send Tasks to Slack", key="send_button"):
            with st.spinner("Sending to Slack..."):
                try:
                    # Format message
                    slack_message = f"*📋 Tasks Extracted from #{channel_name}*\n\n"
                    
                    for i, task in enumerate(sorted_tasks, 1):
                        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[task["priority"]]
                        slack_message += f"{priority_emoji} *Task {i}:* {task['task']}\n"
                        slack_message += f"• *Action:* {task['action'].capitalize()}\n"
                        slack_message += f"• *Assignee:* {task['assignee']}\n"
                        slack_message += f"• *Priority:* {task['priority'].capitalize()}\n"
                        if task['due_date']:
                            slack_message += f"• *Due Date:* {task['due_date']}\n"
                        slack_message += "\n"
                    
                    # Send message
                    client.chat_postMessage(channel=channel_id, text=slack_message)
                    st.success("✅ Tasks sent to Slack successfully!")
                    st.balloons()
                    
                except SlackApiError as e:
                    st.error(f"Error sending message: {e.response['error']}")
    
    elif channel_id:
        st.info("👆 Click 'Extract Tasks' to analyze the selected Slack channel.")
    
with col2:
    # Task Assignment Panel
    st.markdown('<h2 class="section-header">👥 Task Management</h2>', unsafe_allow_html=True)
    
    # Fetch workspace users for assignment
    try:
        users_response = client.users_list()
        users = {user["name"]: user["id"] for user in users_response["members"] if not user["is_bot"]}
        
        with st.form("task_assignment_form"):
            st.subheader("Assign Tasks")
            
            task_index = st.selectbox(
                "Select Task", 
                options=list(range(1, len(st.session_state.tasks) + 1)) if st.session_state.tasks else [],
                format_func=lambda x: f"Task {x}: {st.session_state.tasks[x-1]['task'][:40]}..." if st.session_state.tasks else ""
            )
            
            assignee = st.selectbox("Assign to", options=list(users.keys()))
            
            priority = st.select_slider(
                "Priority", 
                options=["low", "medium", "high"],
                value="medium"
            )
            
            due_date = st.date_input("Due Date", value=datetime.now() + timedelta(days=3))
            
            submitted = st.form_submit_button("Assign Task")
            
            if submitted and st.session_state.tasks and task_index <= len(st.session_state.tasks):
                # Update task assignment
                st.session_state.tasks[task_index-1]["assignee"] = assignee
                st.session_state.tasks[task_index-1]["priority"] = priority
                st.session_state.tasks[task_index-1]["due_date"] = due_date.strftime("%Y-%m-%d")
                
                # Track assignments
                if assignee not in st.session_state.assigned_users:
                    st.session_state.assigned_users[assignee] = 0
                st.session_state.assigned_users[assignee] += 1
                
                st.success(f"Task {task_index} assigned to {assignee}")
    
    except Exception as e:
        st.warning(f"Could not fetch users: {e}")
    
    # History and Analytics
    st.markdown('<h3 class="section-header">📊 Analytics</h3>', unsafe_allow_html=True)
    
    if st.session_state.history:
        st.subheader("Recent Extractions")
        for i, record in enumerate(reversed(st.session_state.history[-5:])):
            st.markdown(
                f"""
                <div style="padding: 10px; border-bottom: 1px solid #ddd;">
                    {record['timestamp']} - Extracted {record['task_count']} tasks from #{record['channel']}
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # User Assignment Stats
    if st.session_state.assigned_users:
        st.subheader("Task Distribution")
        
        for user, count in sorted(st.session_state.assigned_users.items(), key=lambda x: x[1], reverse=True):
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="width: 120px;">{user}</span>
                    <div style="background-color: #4A154B; height: 15px; width: {min(count*50, 200)}px;"></div>
                    <span style="margin-left: 10px;">{count}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

# Footer
st.markdown("---")
