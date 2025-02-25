from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
options = Options()
options.add_argument("--user-data-dir=C:\\Users\\kalya\\AppData\\Local\\Google\\Chrome\\User Data")
options.add_argument("--profile-directory=Default")  
options.add_experimental_option('excludeSwitches', ['enable-logging']) 
chrome_driver_path = "C:\\Program Files\\ChromeDriver\\chromedriver.exe"
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

driver.get("https://web.whatsapp.com")
input("Press Enter after scanning QR code...")
