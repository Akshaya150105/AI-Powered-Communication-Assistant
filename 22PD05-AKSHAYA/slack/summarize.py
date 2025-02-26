import streamlit as st
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from transformers import pipeline
import time

# Page configuration
st.set_page_config(
    page_title="Slack Channel Summarizer",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: bold;
        background-color: #4A154B;
        color: white;
    }
    .stButton > button:hover {
        background-color: #611f64;
    }
    .summary-box {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #4A154B;
    }
    h1, h2, h3 {
        color: #4A154B;
    }
</style>
""", unsafe_allow_html=True)

# App title with logo
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://cdn.cdnlogo.com/logos/s/40/slack.svg", width=60)
with col2:
    st.title("Slack Channel Message Summarizer")

st.markdown("---")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Token input with password field
    api_token = st.text_input(
        "Slack Bot Token",
        value="xoxb-8497485985891-8494927306197-YWinmCEXrlbf2oz2N7I9TLw3",
        type="password",
        help="Your Slack Bot Token starting with 'xoxb-'"
    )
    
    # Model selection
    model_option = st.selectbox(
        "Summarization Model",
        options=["facebook/bart-large-cnn", "google/pegasus-xsum", "t5-small"],
        index=0,
        help="Select the AI model for text summarization"
    )
    
    # Advanced options
    with st.expander("Advanced Options"):
        max_length = st.slider("Max Summary Length", 30, 200, 100)
        min_length = st.slider("Min Summary Length", 10, 50, 30)
        message_limit = st.number_input("Message Limit", 10, 1000, 100)
        chunk_size = st.number_input("Chunk Size (# of messages per summarization)", 5, 50, 20, 
                                     help="Break down large conversations into smaller chunks")
        
    st.markdown("---")
    st.markdown("### About")
    st.markdown("This app summarizes messages from Slack channels using transformer-based AI models.")

# Initialize client only when API token is provided
@st.cache_resource(show_spinner=False)
def get_slack_client(token):
    return WebClient(token=token)

# Initialize summarizer with selected model
@st.cache_resource(show_spinner=False)
def get_summarizer(model_name):
    return pipeline("summarization", model=model_name)

# Main functions
def get_channel_id(client, channel_name):
    """Fetch the ID of a channel by name."""
    try:
        with st.spinner(f"Finding channel '{channel_name}'..."):
            response = client.conversations_list()
            if response["ok"]:
                for channel in response["channels"]:
                    if channel["name"] == channel_name:
                        return channel["id"]
            return None
    except SlackApiError as e:
        st.error(f"Slack API Error: {e.response['error']}")
        return None

def fetch_messages(client, channel_id, include_usernames, limit):
    """Fetch messages from a Slack channel, excluding bot messages."""
    try:
        with st.spinner("Fetching messages..."):
            response = client.conversations_history(channel=channel_id, limit=limit)
            if response["ok"]:
                messages = []
                for msg in response["messages"]:
                    # Skip messages that:
                    # 1. Have a bot_id (sent by bots)
                    # 2. Have certain subtypes that indicate automated messages
                    # 3. Don't have text content
                    if ("bot_id" not in msg and 
                        "text" in msg and 
                        not msg.get("subtype")):
                        
                        if include_usernames and "user" in msg:
                            try:
                                user_info = client.users_info(user=msg["user"])
                                username = user_info["user"]["real_name"] if user_info["ok"] else "Unknown"
                                messages.append(f"{username}: {msg['text']}")
                            except:
                                messages.append(msg["text"])
                        else:
                            messages.append(msg["text"])
                return messages
            return []
    except SlackApiError as e:
        st.error(f"Slack API Error: {e.response['error']}")
        return []

def chunk_messages(messages, chunk_size):
    """Break down messages into manageable chunks."""
    return [messages[i:i + chunk_size] for i in range(0, len(messages), chunk_size)]

def summarize_chunk(summarizer, messages, max_len, min_len):
    """Summarize a chunk of messages."""
    if not messages:
        return ""
    
    # Filter out very short messages
    filtered_messages = [msg for msg in messages if len(msg.split()) > 2]
    
    if not filtered_messages:
        return ""
    
    # Join messages with space, keeping them short enough
    text = " ".join(filtered_messages)
    
    # Limit text length to what models can typically handle
    text = text[:4000]  
    
    try:
        summary = summarizer(
            text,
            max_length=max_len,
            min_length=min_len,
            do_sample=False
        )[0]["summary_text"]
        return summary
    except Exception as e:
        st.warning(f"Warning during summarization of a chunk: {str(e)}")
        # Fallback: return the first few messages if summarization fails
        return " ".join(filtered_messages[:3]) + "..."

def summarize_messages(summarizer, messages, max_len, min_len, chunk_size):
    """Summarize messages by breaking them into chunks."""
    if not messages:
        return "No messages found to summarize."
    
    with st.spinner("Generating summary..."):
        # Break messages into chunks
        message_chunks = chunk_messages(messages, chunk_size)
        
        # Summarize each chunk
        chunk_summaries = []
        progress_bar = st.progress(0)
        
        for i, chunk in enumerate(message_chunks):
            chunk_summary = summarize_chunk(summarizer, chunk, max_len, min_len)
            if chunk_summary:
                chunk_summaries.append(chunk_summary)
            progress_bar.progress((i + 1) / len(message_chunks))
        
        if not chunk_summaries:
            return "Could not generate a summary from the messages."
        
        # If we have multiple chunk summaries, summarize them again
        if len(chunk_summaries) > 1:
            # Join the chunk summaries
            final_text = " ".join(chunk_summaries)
            
            try:
                # Attempt to create a final summary
                final_summary = summarizer(
                    final_text[:4000],  # Limit input size
                    max_length=max_len,
                    min_length=min_len,
                    do_sample=False
                )[0]["summary_text"]
                return final_summary
            except:
                # If that fails, return the combined chunk summaries
                return " ".join(chunk_summaries)
        else:
            # If we only have one chunk summary, return it
            return chunk_summaries[0]

# Main app area
with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        channel_names = st.text_input(
            "Enter channel names (comma-separated)",
            placeholder="general, random, team-updates"
        )
    
    with col2:
        include_usernames = st.checkbox("Include usernames in messages", value=True)
        show_raw_messages = st.checkbox("Show raw messages", value=False)

# Process button
if st.button("🔍 Fetch and Summarize Messages"):
    if not api_token:
        st.error("Please enter a valid Slack Bot Token")
    elif not channel_names:
        st.warning("Please enter at least one channel name")
    else:
        client = get_slack_client(api_token)
        summarizer = get_summarizer(model_option)
        
        channels = [name.strip() for name in channel_names.split(",")]
        
        # Create tabs for each channel
        if len(channels) > 0:
            tabs = st.tabs([f"#{channel}" for channel in channels])
            
            for i, channel in enumerate(channels):
                with tabs[i]:
                    channel_id = get_channel_id(client, channel)
                    
                    if channel_id:
                        st.success(f"Channel '#{channel}' found!")
                        
                        messages = fetch_messages(
                            client, 
                            channel_id, 
                            include_usernames, 
                            message_limit
                        )
                        
                        if messages:
                            summary = summarize_messages(
                                summarizer, 
                                messages, 
                                max_length, 
                                min_length,
                                chunk_size
                            )
                            
                            # Display summary
                            st.subheader("📝 Summary")
                            st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)
                            
                            # Display metrics
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Messages Analyzed", len(messages))
                            col2.metric("Characters", len(" ".join(messages)))
                            col3.metric("Summary Length", len(summary))
                            
                            # Option to download summary
                            st.download_button(
                                label="Download Summary",
                                data=summary,
                                file_name=f"summary-{channel}.txt",
                                mime="text/plain"
                            )
                            
                            # Option to show raw messages
                            if show_raw_messages:
                                with st.expander("Raw Messages"):
                                    for msg in messages[:20]:  # Limit display to 20 messages
                                        st.markdown(f"- {msg}")
                                    if len(messages) > 20:
                                        st.info(f"{len(messages) - 20} more messages not shown")
                        else:
                            st.warning("No messages found in this channel.")
                    else:
                        st.error(f"Could not find channel '#{channel}'. Make sure the name is correct and your bot has access to it.")

# Add a footer
st.markdown("---")
st.caption("Powered by Streamlit and Hugging Face Transformers")