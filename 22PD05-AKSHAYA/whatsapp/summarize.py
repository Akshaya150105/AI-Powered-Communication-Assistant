import streamlit as st
import time
import torch
import os
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from transformers import BartForConditionalGeneration, BartTokenizer

# Set page configuration
st.set_page_config(
    page_title="WhatsApp Chat Summarizer",
    page_icon="💬",
    layout="wide"
)

# App title and description
st.title("💬 WhatsApp Chat Summarizer")
st.markdown("This app allows you to extract and summarize WhatsApp conversations.")

# Initialize session state variables
if 'driver' not in st.session_state:
    st.session_state.driver = None
if 'model' not in st.session_state:
    st.session_state.model = None
if 'tokenizer' not in st.session_state:
    st.session_state.tokenizer = None
if 'is_loaded' not in st.session_state:
    st.session_state.is_loaded = False
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'summary' not in st.session_state:
    st.session_state.summary = ""
if 'full_text' not in st.session_state:
    st.session_state.full_text = ""
if 'chat_name' not in st.session_state:
    st.session_state.chat_name = ""

# Sidebar for setup
with st.sidebar:
    st.header("Setup")
    
    # Chrome settings
    st.subheader("Chrome Settings")
    user_data_dir = st.text_input("Chrome User Data Directory", value="C:\\Users\\Aparna\\AppData\\Local\\Google\\Chrome\\User Data")
    profile_dir = st.text_input("Chrome Profile Directory", value="Profile 13")
    chrome_driver_path = st.text_input("ChromeDriver Path", value="C:\\Program Files\\ChromeDriver\\chromedriver.exe")
    
    # Loading BART model
    st.subheader("BART Model")
    model_name = st.selectbox("Select BART Model", ["facebook/bart-large-cnn"], index=0)
    
    # Load model and initialize driver
    if st.button("Initialize System"):
        with st.spinner("Loading BART model..."):
            try:
                @st.cache_resource
                def load_model(model_name):
                    tokenizer = BartTokenizer.from_pretrained(model_name)
                    model = BartForConditionalGeneration.from_pretrained(model_name)
                    return tokenizer, model
                
                st.session_state.tokenizer, st.session_state.model = load_model(model_name)
                st.success("✅ BART model loaded successfully!")
                
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
            except Exception as e:
                st.error(f"Error initializing system: {e}")

# Main content
if st.session_state.is_loaded:
    # Check login status
    if not st.session_state.is_logged_in:
        if st.button("I've Scanned the QR Code"):
            time.sleep(5)  # Give extra time to load chats
            st.session_state.is_logged_in = True
            st.success("✅ WhatsApp Web logged in successfully!")
            st.rerun()
    
    # Chat extraction interface
    if st.session_state.is_logged_in:
        st.subheader("Extract Chat")
        chat_name = st.text_input("Enter the name of the chat/contact to extract")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Extract Messages", key="extract_button"):
                if not chat_name:
                    st.warning("Please enter a chat name.")
                else:
                    st.session_state.chat_name = chat_name
                    with st.spinner(f"Extracting messages from '{chat_name}'..."):
                        try:
                            # Search for the chat
                            search_box = WebDriverWait(st.session_state.driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                            )
                            search_box.clear()
                            search_box.send_keys(chat_name)
                            time.sleep(3)

                            # Click on chat if found
                            try:
                                chat = WebDriverWait(st.session_state.driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, f"//span[@title='{chat_name}']"))
                                )
                                chat.click()
                                st.success(f"✅ Opened chat: {chat_name}")
                            except:
                                st.error("⚠️ Chat not found! Ensure the contact name is correct.")
                                st.stop()

                            time.sleep(3)

                            # Scroll to load more messages
                            last_height = st.session_state.driver.execute_script("return document.body.scrollHeight")
                            progress_bar = st.progress(0)
                            for i in range(5):  # Scroll multiple times
                                st.session_state.driver.execute_script("window.scrollTo(0, 0);")
                                time.sleep(1)
                                progress_bar.progress((i + 1) / 5)

                            # Expand all "Read more" buttons
                            st.info("Expanding 'Read more' buttons...")
                            expanded_count = 0
                            while True:
                                read_more_buttons = st.session_state.driver.find_elements(By.XPATH, "//span[contains(text(),'Read more')]")
                                if not read_more_buttons:
                                    break
                                for btn in read_more_buttons:
                                    try:
                                        st.session_state.driver.execute_script("arguments[0].scrollIntoView();", btn)
                                        time.sleep(0.5)
                                        st.session_state.driver.execute_script("arguments[0].click();", btn)
                                        time.sleep(1)
                                        expanded_count += 1
                                    except Exception as e:
                                        st.warning(f"Error clicking 'Read more' button: {e}")
                                        continue
                            
                            if expanded_count > 0:
                                st.info(f"Expanded {expanded_count} 'Read more' buttons")
                            time.sleep(2)  # Wait to ensure all messages are expanded

                            # Extract messages
                            messages = st.session_state.driver.find_elements(By.XPATH, "//div[contains(@class,'message-in') or contains(@class,'message-out')]//span[contains(@class,'selectable-text')]")
                            st.info(f"Found {len(messages)} messages")

                            chat_text = []
                            for msg in messages:
                                try:
                                    text = msg.text.strip()
                                    if text:
                                        chat_text.append(text)
                                except Exception as e:
                                    st.warning(f"Error extracting message: {e}")
                                    continue

                            if not chat_text:
                                st.error("⚠️ No messages found. Something went wrong!")
                                st.stop()

                            st.session_state.messages = chat_text
                            st.session_state.full_text = " ".join(chat_text)
                            
                            # Save full chat
                            with open(f"full_chat_{chat_name}.txt", "w", encoding="utf-8") as file:
                                file.write(st.session_state.full_text)
                            st.success(f"✅ Full chat saved as 'full_chat_{chat_name}.txt'")
                            
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
        
        with col2:
            if st.button("Summarize Chat", key="summarize_button", disabled=not st.session_state.messages):
                with st.spinner("Summarizing chat..."):
                    try:
                        # Summarize chat using BART
                        def summarize_chat(text):
                            inputs = st.session_state.tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
                            summary_ids = st.session_state.model.generate(
                                inputs["input_ids"], 
                                max_length=200, 
                                min_length=50, 
                                length_penalty=2.0, 
                                num_beams=4, 
                                early_stopping=True
                            )
                            return st.session_state.tokenizer.decode(summary_ids[0], skip_special_tokens=True)

                        st.session_state.summary = summarize_chat(st.session_state.full_text)
                        
                        # Save chat summary
                        with open(f"chat_summary_{st.session_state.chat_name}.txt", "w", encoding="utf-8") as file:
                            file.write(st.session_state.summary)
                        st.success(f"✅ Chat summary saved as 'chat_summary_{st.session_state.chat_name}.txt'")
                    
                    except Exception as e:
                        st.error(f"❌ Error summarizing chat: {e}")

        # Display results in tabs
        if st.session_state.messages:
            tabs = st.tabs(["Messages", "Summary", "Full Text"])
            
            with tabs[0]:
                st.subheader(f"Messages from '{st.session_state.chat_name}'")
                for i, msg in enumerate(st.session_state.messages):
                    st.text(f"{i+1}. {msg}")
            
            with tabs[1]:
                st.subheader("Chat Summary")
                if st.session_state.summary:
                    st.write(st.session_state.summary)
                else:
                    st.info("Click 'Summarize Chat' to generate a summary.")
            
            with tabs[2]:
                st.subheader("Full Text")
                st.text_area("", value=st.session_state.full_text, height=300, disabled=True)
                
                if st.download_button(
                    label="Download Full Chat",
                    data=st.session_state.full_text,
                    file_name=f"full_chat_{st.session_state.chat_name}.txt",
                    mime="text/plain"
                ):
                    st.success("Download started!")

# Add cleanup when app is closed
def cleanup():
    if st.session_state.driver:
        st.session_state.driver.quit()

# Register the cleanup function
import atexit
atexit.register(cleanup)

# Footer
st.markdown("---")
st.markdown("Created with Streamlit and BART summarization model")