import time
import torch
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from transformers import BartForConditionalGeneration, BartTokenizer

# 🔹 Load BART Model & Tokenizer
model_name = "facebook/bart-large-cnn"
tokenizer = BartTokenizer.from_pretrained(model_name)
model = BartForConditionalGeneration.from_pretrained(model_name)

# 🔹 Chrome Driver Setup
options = Options()
options.add_argument("--user-data-dir=C:\\Users\\kalya\\AppData\\Local\\Google\\Chrome\\User Data")
options.add_argument("--profile-directory=Default")  
options.add_experimental_option('excludeSwitches', ['enable-logging']) 

chrome_driver_path = "C:\\Program Files\\ChromeDriver\\chromedriver.exe"
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

# 🔹 Open WhatsApp Web
driver.get("https://web.whatsapp.com")
input("Press Enter after scanning QR code...")  
time.sleep(5)  # Give extra time to load chats

while True:  
    try:
        # 🔹 Get chat name
        chat_name = input("\nEnter the chat name (or type 'exit' to quit): ")
        if chat_name.lower() == "exit":
            print("🚪 Exiting program...")
            break  
        
        # 🔹 Search for the chat
        search_box = driver.find_element(By.XPATH, "//div[@contenteditable='true']")
        search_box.clear()
        search_box.send_keys(chat_name)
        time.sleep(3)

        # 🔹 Click on chat if found
        try:
            chat = driver.find_element(By.XPATH, f"//span[@title='{chat_name}']")
            chat.click()
            print(f"✅ Opened chat: {chat_name}")
        except:
            print("⚠️ Chat not found! Ensure the contact name is correct.")
            continue  

        time.sleep(3)

        # 🔹 Scroll to load more messages
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):  # Scroll multiple times to ensure all messages load
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

        # 🔹 Click all "Read more" buttons
        def expand_read_more():
            read_more_buttons = driver.find_elements(By.XPATH, "//span[contains(text(),'Read more')]")
            for btn in read_more_buttons:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)  
                    print("🔹 Clicked 'Read more' button")
                except Exception as e:
                    print(f"❌ Error clicking 'Read more' button: {e}")
                    continue  

        expand_read_more()
        time.sleep(2)  # Wait to ensure all messages are expanded

        # 🔹 Extract messages
        messages = driver.find_elements(By.XPATH, "//div[contains(@class,'message-in') or contains(@class,'message-out')]//span[contains(@class,'selectable-text')]")
        print(f"🔹 Found {len(messages)} messages")

        chat_text = []
        for msg in messages:
            try:
                text = msg.text.strip()
                if text:
                    chat_text.append(text)
                    print(f"📩 Message: {text}")  # ✅ Print each extracted message
            except Exception as e:
                print(f"❌ Error extracting message: {e}")
                continue

        if not chat_text:
            print("⚠️ No messages found. Something went wrong!")
            continue  

        full_text = " ".join(chat_text)

        # 🔹 Save full chat before summarization
        with open(f"full_chat_{chat_name}.txt", "w", encoding="utf-8") as file:
            file.write(full_text)
        print(f"\n✅ Full chat saved as 'full_chat_{chat_name}.txt'")

        # 🔹 Summarize chat using BART
        def summarize_chat(text):
            inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
            summary_ids = model.generate(inputs["input_ids"], max_length=200, min_length=50, length_penalty=2.0, num_beams=4, early_stopping=True)
            return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

        chat_summary = summarize_chat(full_text)

        # 🔹 Save chat summary
        with open(f"chat_summary_{chat_name}.txt", "w", encoding="utf-8") as file:
            file.write(chat_summary)

        print(f"\n✅ Chat summary saved as 'chat_summary_{chat_name}.txt'")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        continue  

# 🔹 Close browser when done
driver.quit()
print("✅ Program closed successfully.")