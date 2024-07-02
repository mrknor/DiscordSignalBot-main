import pyautogui
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from secret import Secret

# Set up the coordinates for the Buy and Sell buttons
BUY_BUTTON_COORDS = (3389, 1345)
SELL_BUTTON_COORDS = (3661, 1345)

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--start-maximized")

# Initialize the browser (Chrome)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

# Selectors for the login page elements
USERNAME_SELECTOR = 'input[name="userName"]'
PASSWORD_SELECTOR = 'input[name="password"]'
LOGIN_BUTTON_SELECTOR = 'button.MuiButtonBase-root.MuiButton-root.MuiButton-contained.MuiButton-containedPrimary.MuiButton-sizeMedium.MuiButton-containedSizeMedium.css-17f09g2'

def open_trading_page():
    # Open the trading page
    driver.get("https://topstepx.com/trade")
    time.sleep(10)  # Wait for the page to load (adjust as needed)
    
    # Enter username and password
    driver.find_element(By.CSS_SELECTOR, USERNAME_SELECTOR).send_keys(Secret.USERNAME)
    driver.find_element(By.CSS_SELECTOR, PASSWORD_SELECTOR).send_keys(Secret.PASSWORD)
    
    # Click the login button
    driver.find_element(By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR).click()
    time.sleep(10)  # Wait for the login to complete (adjust as needed)

def click_button(coords):
    pyautogui.moveTo(coords)
    pyautogui.click()

def execute_trade(signal_type):
    if signal_type == 'LONG':
        click_button(BUY_BUTTON_COORDS)
    elif signal_type == 'SHORT':
        click_button(SELL_BUTTON_COORDS)

def setup_and_click(signal_type):
    # Bring the browser window to the front
    driver.switch_to.window(driver.current_window_handle)
    execute_trade(signal_type)
    time.sleep(1)  # Add a delay to ensure the click is registered
