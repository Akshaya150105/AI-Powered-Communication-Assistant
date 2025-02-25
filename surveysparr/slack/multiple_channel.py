import streamlit as st
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

# Initialize Slack Client
SLACK_BOT_TOKEN = "xoxb-8497485985891-8494927306197-YWinmCEXrlbf2oz2N7I9TLw3"
client = WebClient(token=SLACK_BOT_TOKEN)

def get_channel_id(channel_name):
    """Fetch the ID of a channel by name."""
    try:
        response = client.conversations_list()
        if response["ok"]:
            for channel in response["channels"]:
                if channel["name"] == channel_name:
                    return channel["id"]
        st.error(f"❌ Channel '{channel_name}' not found.")
    except SlackApiError as e:
        st.error(f"Slack API Error: {e.response['error']}")
    return None

def fetch_messages(channel_id):
    """Fetch messages from a Slack channel and filter out bot/system messages."""
    try:
        response = client.conversations_history(channel=channel_id)
        if response["ok"]:
            messages = []
            for msg in response["messages"]:
                if "text" in msg and not msg.get("subtype") and not msg.get("bot_id"):
                    messages.append(msg["text"])
            messages = list(set(messages))  # Remove duplicates
            return messages
    except SlackApiError as e:
        st.error(f"Slack API Error: {e.response['error']}")
    return []

def summarize_messages(messages):
    """Summarize messages using LexRank."""
    if not messages:
        return "No messages found."
    
    messages = list(set([msg.strip() for msg in messages if len(msg.split()) > 3]))
    text = " ".join(messages)
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    summary_sentences = summarizer(parser.document)  # Default to 3 sentences
    summary = "\n".join(str(sentence) for sentence in summary_sentences)
    
    return summary if summary else "No key messages found."

st.title("📢 Slack Channel Message Summarizer")

channel_names = st.text_input("Enter channel names (comma-separated)")
include_usernames = st.checkbox("Include usernames in messages")

def fetch_messages_with_usernames(channel_id):
    """Fetch messages along with usernames from a Slack channel, filtering out bot/system messages."""
    try:
        response = client.conversations_history(channel=channel_id)
        if response["ok"]:
            messages = []
            for msg in response["messages"]:
                if "text" in msg and not msg.get("subtype") and not msg.get("bot_id"):
                    user_info = client.users_info(user=msg.get("user", "")) if "user" in msg else None
                    username = user_info["user"]["real_name"] if user_info and user_info["ok"] else "Unknown"
                    messages.append(f"{username}: {msg['text']}" if include_usernames else msg["text"])
            messages = list(set(messages))  # Remove duplicates
            return messages
    except SlackApiError as e:
        st.error(f"Slack API Error: {e.response['error']}")
    return []

if st.button("Fetch and Summarize Messages"):
    if channel_names:
        channels = [name.strip() for name in channel_names.split(",")]
        for channel in channels:
            channel_id = get_channel_id(channel)
            if channel_id:
                messages = fetch_messages_with_usernames(channel_id) if include_usernames else fetch_messages(channel_id)
                summary = summarize_messages(messages)
                st.subheader(f"🔹 Summary for #{channel}")
                st.text_area("Summary:", summary, height=150)
    else:
        st.warning("Please enter at least one channel name.")
