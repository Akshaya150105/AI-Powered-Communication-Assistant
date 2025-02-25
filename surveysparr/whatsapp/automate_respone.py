import time
import nltk
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Set up Chrome options
options = Options()
options.add_argument("--user-data-dir=C:\\Users\\kalya\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 8")  
options.add_argument("--profile-directory=Profile 8")
options.add_experimental_option('excludeSwitches', ['enable-logging'])  

chrome_driver_path = "C:\\Program Files\\ChromeDriver\\chromedriver.exe"
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

# Open WhatsApp Web
driver.get("https://web.whatsapp.com")
input("Press Enter after scanning QR code...")  # Wait for manual login

# Define a simple AI-powered response system
responses = {
    "hi": ["Hello!", "Hi there!", "Hey! How can I help?"],
    "working hours": ["Our working hours are 9 AM - 6 PM.", "We operate from 9 AM to 6 PM, Monday to Friday."],
    "services": ["We offer AI automation, chatbot development, and data analytics services."],
    "default": ["I'm not sure about that. Can you clarify?", "Sorry, I don't understand. Can you rephrase?"]
}

# Function to generate a response
def generate_response(message):
    message = message.lower()
    for key in responses.keys():
        if key in message:
            return random.choice(responses[key])
    return random.choice(responses["default"])

# Function to monitor messages and reply
def auto_reply():
    while True:
        try:
            # Get unread messages
            unread_messages = driver.find_elements(By.CLASS_NAME, "_1pJ9J")  # WhatsApp unread message indicator
            if unread_messages:
                unread_messages[-1].click()  # Open latest unread chat
                time.sleep(2)

                # Extract the last received message
                chat_messages = driver.find_elements(By.XPATH, "//div[@class='_1Gy50']")
                if chat_messages:
                    last_message = chat_messages[-1].text
                    print(f"Received: {last_message}")

                    # Generate a response
                    response = generate_response(last_message)
                    print(f"Replying: {response}")

                    # Send response
                    message_box = driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")
                    message_box.send_keys(response)
                    message_box.send_keys(Keys.ENTER)
                    time.sleep(2)

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(5)  # Check for new messages every 5 seconds

# Start auto-reply system
auto_reply()
