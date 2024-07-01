import pyautogui
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Set up the coordinates for the Buy and Sell buttons
BUY_BUTTON_COORDS = (3389, 1345)
SELL_BUTTON_COORDS = (3661, 1345)

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--start-maximized")

# Initialize the browser (Chrome)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

def open_trading_page():
    # Open the trading page
    driver.get("https://topstepx.com/trade")
    # Wait for the page to load (you might need to adjust the sleep duration)
    time.sleep(10)  # Adjust as needed based on your network speed and page load time

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
