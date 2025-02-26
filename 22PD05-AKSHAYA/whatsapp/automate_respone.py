import streamlit as st
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import time
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="WhatsApp Business AI Assistant",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS for WhatsApp-like styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #e5ddd5;
        background-image: url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png");
        background-size: cover;
    }
    
    /* Header styling */
    .chat-header {
        background-color: #075E54;
        color: white;
        padding: 10px;
        border-radius: 10px 10px 0 0;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
    }
    
    /* Chat message containers */
    .user-message {
        background-color: #dcf8c6;
        padding: 10px 15px;
        border-radius: 7.5px;
        margin: 5px 0;
        max-width: 70%;
        margin-left: auto;
        position: relative;
        word-wrap: break-word;
    }
    
    .bot-message {
        background-color: white;
        padding: 10px 15px;
        border-radius: 7.5px;
        margin: 5px 0;
        max-width: 70%;
        position: relative;
        word-wrap: break-word;
    }
    
    /* Message time styling */
    .message-time {
        color: rgba(0, 0, 0, 0.45);
        font-size: 0.7em;
        text-align: right;
        margin-top: 3px;
    }
    
    /* Input area styling */
    .chat-input {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 0 0 10px 10px;
        display: flex;
        align-items: center;
    }
    
    /* Custom styling for the chat container */
    .chat-container {
        background-color: #e5ddd5;
        border-radius: 10px;
        margin: 0 auto;
        max-width: 600px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
    }
    
    /* Hide Streamlit elements we don't need */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    
    /* Style the send button */
    .stButton button {
        background-color: #128C7E;
        color: white;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_model():
    """Load the fine-tuned model and tokenizer"""
    model_path = "P:\\aks\\pages\\whatsapp\\fine_tuned_dialoGPT"

    if os.path.exists(model_path):
        try:
            st.info("Loading fine-tuned WhatsApp Business model...")
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(model_path)
            st.success("Fine-tuned model loaded successfully!")
            return tokenizer, model
        except Exception as e:
            st.error(f"Error loading fine-tuned model: {e}")
    else:
        st.warning("Fine-tuned model not found. Loading base DialoGPT model instead.")
    
    
    tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
    model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")
    return tokenizer, model

def generate_response(input_text, tokenizer, model):
    """Generate a response using the loaded model"""
    # Encode the input text
    input_ids = tokenizer.encode(input_text + tokenizer.eos_token, return_tensors='pt')
    
    # Create attention mask
    attention_mask = torch.ones_like(input_ids)
    
    # Generate a response
    with torch.no_grad():
        output = model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_length=150,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id,
            temperature=0.7,
            top_k=50,
            top_p=0.9,
            do_sample=True,
            no_repeat_ngram_size=3,
            length_penalty=1.0
        )
    
    # Decode the response
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    
    # Remove the input from the response if present
    if input_text in response:
        response = response.replace(input_text, "").strip()
    
    return response

def get_current_time():
    """Get current time formatted for chat messages"""
    return datetime.now().strftime("%I:%M %p")

# Initialize chat history in session state if it doesn't exist
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Initialize typing state
if 'typing' not in st.session_state:
    st.session_state.typing = False

# Initialize input state
if 'input_value' not in st.session_state:
    st.session_state.input_value = ""

# Function to clear input after sending
def clear_input():
    st.session_state.input_value = ""

# Function to handle message submission
def handle_submit():
    # Get the input value from the text field
    input_value = st.session_state.user_input
    
    if input_value:
        # Add user message to chat history
        current_time = get_current_time()
        st.session_state.chat_history.append({
            'text': input_value,
            'is_user': True,
            'time': current_time
        })
        
        # Set flag to clear input on next rerun
        st.session_state.input_value = ""
        
        # Generate response
        response = generate_response(input_value, tokenizer, model)
        
        # Simulate typing delay based on response length
        typing_placeholder = st.empty()
        typing_placeholder.markdown("""
        <div class="bot-message" style="width: fit-content;">
            Typing<span id="typing-animation">...</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Add a delay based on message length
        delay = min(3, max(1, len(response) * 0.01))  # Between 1 and 3 seconds
        time.sleep(delay)
        
        # Clear typing indicator
        typing_placeholder.empty()
        
        # Add bot response to chat history
        st.session_state.chat_history.append({
            'text': response,
            'is_user': False,
            'time': get_current_time()
        })

# Load the model
tokenizer, model = load_model()

# App title and header
st.markdown("""
<div class="chat-container">
    <div class="chat-header">
        <h3 style="margin: 0;">🤖 WhatsApp Business AI Assistant</h3>
    </div>
""", unsafe_allow_html=True)

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        if message['is_user']:
            st.markdown(f"""
            <div class="user-message">
                {message['text']}
                <div class="message-time">{message['time']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="bot-message">
                {message['text']}
                <div class="message-time">{message['time']}</div>
            </div>
            """, unsafe_allow_html=True)

# Input area
st.markdown('<div class="chat-input">', unsafe_allow_html=True)
col1, col2 = st.columns([5, 1])

with col1:
    st.text_input("Type a message...", key="user_input", value=st.session_state.input_value, label_visibility="collapsed")

with col2:
    if st.button("📤", key="send"):
        handle_submit()

st.markdown('</div></div>', unsafe_allow_html=True)

# Display a welcome message if no messages yet
if not st.session_state.chat_history:
    st.markdown("""
    <div class="bot-message">
        Hello! 👋 I'm your WhatsApp Business AI Assistant. How can I help you today?
        <div class="message-time">just now</div>
    </div>
    """, unsafe_allow_html=True)