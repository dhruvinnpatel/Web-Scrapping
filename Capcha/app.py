import easyocr
import cv2
import numpy as np
import re
import time
import requests
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

def initialize_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.page_load_strategy = 'eager'  # Load strategy
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def select_radio_button(driver, radio_button_id):
    radio_button = driver.find_element(By.ID, radio_button_id)
    if not radio_button.is_selected():
        radio_button.click()

def wait_for_dropdowns_to_enable(driver):
    WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, 'ddSourceState'))
    )
    WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, 'ddSourceDistrict'))
    )

def get_states(driver):
    state_dropdown = Select(driver.find_element(By.ID, 'ddSourceState'))
    states = [option.text for option in state_dropdown.options if option.text and option.text != 'All']
    return states

def get_districts(driver, state):
    state_dropdown = Select(driver.find_element(By.ID, 'ddSourceState'))
    state_dropdown.select_by_visible_text(state)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, 'ddSourceDistrict'))
    )
    district_dropdown = Select(driver.find_element(By.ID, 'ddSourceDistrict'))
    districts = [option.text for option in district_dropdown.options if option.text and option.text != 'All']
    return districts

def ocr_text_from_screenshot(image_path):
    # Perform OCR on the screenshot
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image_path)
    text_output = ""
    for detection in result:
        text_output += detection[1].replace(" ", "")
    clean_text = re.sub(r'[^A-Za-z0-9]', '', text_output)
    return clean_text

def capture_captcha_image(driver, captcha_img_id, screenshot_path):
    captcha_img = driver.find_element(By.ID, captcha_img_id)
    location = captcha_img.location
    size = captcha_img.size
    driver.save_screenshot('full_screenshot.png')

    # Open the full screenshot and crop the CAPTCHA part
    screenshot = Image.open('full_screenshot.png')
    left = location['x']
    top = location['y']
    right = left + size['width']
    bottom = top + size['height']
    captcha_image = screenshot.crop((left, top, right, bottom))
    captcha_image.save(screenshot_path)
    print(f"Captcha image saved as {screenshot_path}")

def fill_captcha(driver, text, field_id):
    captcha_field = driver.find_element(By.ID, field_id)
    captcha_field.send_keys(text.upper())
    
    # Simulate pressing the Enter key to submit the form
    captcha_field.send_keys(u'\ue007')
    
    # Optionally, you can wait for the page to process the CAPTCHA and redirect
    try:
        WebDriverWait(driver, 20).until(
            EC.url_changes(driver.current_url)  # Wait for URL to change, indicating redirection
        )
    except Exception as e:
        print(f"Error while waiting for redirection: {e}")
        driver.save_screenshot('error_screenshot.png')  # Save screenshot for debugging

def select_captcha(driver, captcha_img_id, screenshot_path):
    capture_captcha_image(driver, captcha_img_id, screenshot_path)
    text = ocr_text_from_screenshot(screenshot_path)
    return text

def scrape_data(driver, state, district):
    state_dropdown = Select(driver.find_element(By.ID, 'ddSourceState'))
    district_dropdown = Select(driver.find_element(By.ID, 'ddSourceDistrict'))

    state_dropdown.select_by_visible_text(state)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, 'ddSourceDistrict'))
    )
    district_dropdown.select_by_visible_text(district)
    
    data = driver.find_element(By.ID, 'dataElementID').text
    return data

def main():
    driver = initialize_driver()
    base_url = 'https://lgdirectory.gov.in/globalviewBlockforcitizen.do?OWASP_CSRFTOKEN=9BIZ-BG9E-R461-QGSE-P8VW-O1GE-44RP-NJKO'
    driver.get(base_url)  
    time.sleep(5)
    select_radio_button(driver, 'searchByHierarchy')  
    wait_for_dropdowns_to_enable(driver)
    states = get_states(driver)
    
    # Attempt CAPTCHA verification
    captcha_text = select_captcha(driver, 'captchaImageId', 'captcha_screenshot.png')
    fill_captcha(driver, captcha_text, 'captchaAnswer')

    # Wait until CAPTCHA process completes and redirection is done
    # WebDriverWait(driver, 20).until(
    #     EC.url_changes(base_url)  # Ensures that the URL has changed from the base URL
    # )

    # After redirection, you may need to wait for page load
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, 'somePageElementID'))  # Adjust this to wait for an element on the new page
    )

    all_data = []

    for state in states:
        districts = get_districts(driver, state)
        for district in districts:
            print(f"Scraping data for State: {state}, District: {district}")
            try:
                data = scrape_data(driver, state, district)
                all_data.append({'State': state, 'District': district, 'Data': data})
            except Exception as e:
                print(f"Error while scraping data for State: {state}, District: {district} - {e}")

    # Save data to CSV
    # with open('scraped_data.csv', 'w', newline='') as file:
    #     writer = csv.DictWriter(file, fieldnames=['State', 'District', 'Data'])
    #     writer.writeheader()
    #     writer.writerows(all_data)
    
    driver.quit()

if __name__ == '__main__':
    main()



