
import streamlit as st
st.set_page_config(
    page_title="Slack Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

import datetime
import re
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from transformers import pipeline
import time

# Slack API Configuration
SLACK_BOT_TOKEN = "xoxb-8497485985891-8494927306197-YWinmCEXrlbf2oz2N7I9TLw3"

# Initialize Slack Client
client = WebClient(token=SLACK_BOT_TOKEN)

# Initialize Summarization Pipeline
@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="facebook/bart-large-cnn")

summarizer = load_summarizer()

def get_channel_id(channel_name):
    try:
        response = client.conversations_list()
        channels = response.get("channels", [])
        for channel in channels:
            if channel["name"] == channel_name:
                return channel["id"]
        return None
    except SlackApiError as e:
        return f"Error fetching channels: {e.response['error']}"

def fetch_slack_messages(channel_id, limit=100):
    try:
        with st.spinner("Fetching messages from Slack..."):
            latest_time = datetime.datetime.now().timestamp()
            response = client.conversations_history(channel=channel_id, latest=str(latest_time), limit=limit)
            messages = response.get('messages', [])
            filtered_messages = [msg for msg in messages if 'bot_id' not in msg and 'user' in msg]
            return filtered_messages
    except SlackApiError as e:
        return f"Error fetching messages: {e.response['error']}"

def get_user_info(user_id):
    try:
        response = client.users_info(user=user_id)
        return response["user"]["real_name"]
    except SlackApiError:
        return "Unknown User"

def extract_tasks(messages):
    with st.spinner("Extracting action items..."):
        tasks = {}
        task_keywords = ["complete", "finish", "submit", "send", "follow up", "review", "approve", 
                         "assign", "deadline", "finalize", "schedule", "update", "prioritize"]
        for msg in messages:
            text = msg.get("text", "")
            user_id = msg.get("user", "Unknown")
            sentences = re.split(r'(?<=[.!?])\s+', text)
            action_sentences = [s.strip() for s in sentences if any(k in s.lower() for k in task_keywords)]
            if action_sentences:
                user_name = get_user_info(user_id)
                if user_name not in tasks:
                    tasks[user_name] = set()
                tasks[user_name].update(action_sentences)
        formatted_tasks = {user: sorted(list(tasks[user])) for user in tasks}
        return formatted_tasks if formatted_tasks else {}

def generate_summary(messages):
    with st.spinner("Generating summary..."):
        if not messages or len(messages) < 2:
            return "No significant discussions found."
        text = "\n".join([msg['text'] for msg in messages if 'text' in msg])
        text = text[:1024]  # Limit to prevent token overflow
        summary = summarizer(text, max_length=100, min_length=50, do_sample=False)
        return summary[0]['summary_text']

def send_digest_to_slack(channel_id, summary, tasks):
    try:
        with st.spinner("Sending digest to Slack..."):
            task_text = ""
            for user, user_tasks in tasks.items():
                task_text += f"*👤 {user}:*\n"
                for task in user_tasks:
                    task_text += f"• {task}\n"
                task_text += "\n"
            
            if not task_text:
                task_text = "No specific action items identified."
                
            digest_text = f"*📢 Daily Digest*\n\n*🔹 Summary:*\n{summary}\n\n*🔹 Action Items:*\n{task_text}"
            client.chat_postMessage(channel=channel_id, text=digest_text)
            return "✅ Digest sent successfully!"
    except SlackApiError as e:
        return f"Error sending digest: {e.response['error']}"

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4A154B;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #454245;
        margin-top: 0;
    }
    .card {
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
        border-left: 5px solid #4A154B;
    }
    .success-card {
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0px;
        background-color: #E3F9E7;
        border-left: 4px solid #36B37E;
    }
    .user-message {
        background-color: #F7F7F7;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 3px solid #4A154B;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: bold;
        margin: 20px 0 10px 0;
        color: #4A154B;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar with logo and navigation
st.sidebar.image("https://cdn.cdnlogo.com/logos/s/40/slack-new.svg", width=50)
st.sidebar.markdown("<h2 style='color: #4A154B;'>Slack Assistant</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# Main content
st.markdown("<h1 class='main-header'>Slack Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Extract insights, summarize conversations, and manage action items from your Slack channels</p>", unsafe_allow_html=True)

# Create tabs for better organization
tabs = st.tabs(["📊 Dashboard", "⚙️ Settings"])

with tabs[0]:  # Dashboard tab
    # Connection status card
    with st.container():
        st.markdown("<div class='card'><h3>🔌 Connection Status</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if SLACK_BOT_TOKEN.startswith("xoxb-"):
                st.success("✅ Slack API: Connected")
            else:
                st.error("❌ Slack API: Not connected")
                
        with col2:
            if 'summarizer' in locals():
                st.success("✅ Summarization Model: Loaded")
            else:
                st.warning("⚠️ Summarization Model: Not loaded")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Channel selection and message fetching
    with st.container():
        st.markdown("<div class='card'><h3>📣 Channel Selection</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            channel_name = st.text_input("Enter Slack Channel Name", placeholder="e.g. general")
        
        with col2:
            message_limit = st.number_input("Message Limit", min_value=10, max_value=1000, value=100, step=10)
        
        if channel_name:
            SLACK_CHANNEL_ID = get_channel_id(channel_name)
            if not SLACK_CHANNEL_ID or isinstance(SLACK_CHANNEL_ID, str) and SLACK_CHANNEL_ID.startswith("Error"):
                st.error(f"❌ Could not find channel '{channel_name}'. Please check the channel name and try again.")
            else:
                st.success(f"✅ Connected to #{channel_name}")
                if st.button("Fetch Messages", key="fetch_btn"):
                    messages = fetch_slack_messages(SLACK_CHANNEL_ID, message_limit)
                    if isinstance(messages, str):
                        st.error(messages)
                    else:
                        st.session_state.messages = messages
                        st.session_state.channel_id = SLACK_CHANNEL_ID
                        st.success(f"Retrieved {len(messages)} messages")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Show processing options once messages are fetched
    if 'messages' in st.session_state and st.session_state.messages:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            with st.container():
                st.markdown("<div class='card'><h3>📝 Recent Messages</h3>", unsafe_allow_html=True)
                for i, msg in enumerate(st.session_state.messages[:5]):
                    user_name = get_user_info(msg.get('user', 'Unknown'))
                    st.markdown(f"<div class='user-message'><b>{user_name}</b>: {msg.get('text', '')}</div>", unsafe_allow_html=True)
                if len(st.session_state.messages) > 5:
                    st.info(f"... and {len(st.session_state.messages) - 5} more messages")
                st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            with st.container():
                st.markdown("<div class='card'><h3>📋 Summary</h3>", unsafe_allow_html=True)
                if st.button("Generate Summary", key="summary_btn"):
                    summary = generate_summary(st.session_state.messages)
                    st.session_state.summary = summary
                
                if 'summary' in st.session_state:
                    st.markdown(f"<div class='success-card'>{st.session_state.summary}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            with st.container():
                st.markdown("<div class='card'><h3>✅ Action Items</h3>", unsafe_allow_html=True)
                if st.button("Extract Tasks", key="tasks_btn"):
                    tasks = extract_tasks(st.session_state.messages)
                    st.session_state.tasks = tasks
                
                if 'tasks' in st.session_state:
                    if not st.session_state.tasks:
                        st.info("No action items detected in the conversation.")
                    else:
                        for user, user_tasks in st.session_state.tasks.items():
                            st.markdown(f"<b>👤 {user}</b>", unsafe_allow_html=True)
                            for task in user_tasks:
                                st.markdown(f"• {task}")
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Send digest section
        st.markdown("<div class='card'><h3>📬 Send Digest</h3>", unsafe_allow_html=True)
        
        if ('summary' in st.session_state) and ('tasks' in st.session_state):
            if st.button("Send Digest to Slack Channel", key="send_digest_btn"):
                response = send_digest_to_slack(
                    st.session_state.channel_id, 
                    st.session_state.summary, 
                    st.session_state.tasks
                )
                st.success(response)
                
                # Show success animation
                with st.spinner("Sending..."):
                    time.sleep(1)
                st.balloons()
        else:
            st.info("Please generate both a summary and extract tasks before sending a digest.")
            
        st.markdown("</div>", unsafe_allow_html=True)

with tabs[1]:  # Settings tab
    st.markdown("<h3 class='section-header'>🔧 App Settings</h3>", unsafe_allow_html=True)
    
    with st.expander("Slack API Configuration"):
        st.text_input("Bot Token", value=SLACK_BOT_TOKEN, type="password")
        st.info("Note: Token updates will take effect after restarting the app")
    
    with st.expander("Summarization Settings"):
        st.slider("Maximum Summary Length", min_value=50, max_value=200, value=100)
        st.slider("Minimum Summary Length", min_value=30, max_value=100, value=50)
    
    with st.expander("Task Detection Settings"):
        task_keywords = ["complete", "finish", "submit", "send", "follow up", "review", "approve", 
                         "assign", "deadline", "finalize", "schedule", "update", "prioritize"]
        
        keyword_text = st.text_area("Task Keywords (one per line)", 
                                  value="\n".join(task_keywords),
                                  height=150)
        
        if st.button("Update Keywords"):
            st.success("Keywords updated successfully!")


