import time
import schedule
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Set up Chrome options
options = Options()
options.add_argument("--user-data-dir=C:\\Users\\kalya\\AppData\\Local\\Google\\Chrome\\User Data")  
options.add_argument("--profile-directory=Profile 8")
options.add_experimental_option('excludeSwitches', ['enable-logging'])  

chrome_driver_path = "C:\\Program Files\\ChromeDriver\\chromedriver.exe"
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

# Open WhatsApp Web
driver.get("https://web.whatsapp.com")
input("Press Enter after scanning QR code...")  # Wait for manual login

# Function to send a reminder
def send_reminder(contact_name, message):
    try:
        # Search for contact
        search_box = driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='3']")
        search_box.clear()
        search_box.send_keys(contact_name)
        time.sleep(2)
        search_box.send_keys(Keys.ENTER)

        time.sleep(2)  # Wait for chat to load

        # Send message
        message_box = driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")
        message_box.send_keys(message)
        message_box.send_keys(Keys.ENTER)
        print(f"Reminder sent to {contact_name}")
    except Exception as e:
        print(f"Error: {e}")

# Get contact name and message from user
contact_name = input("Enter the contact name: ")
reminder_message = input("Enter the reminder message: ")
reminder_time = input("Enter the time (HH:MM in 24-hour format): ")

# Schedule the reminder
schedule.every().day.at(reminder_time).do(send_reminder, contact_name=contact_name, message=reminder_message)

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute