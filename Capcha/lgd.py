import easyocr, cv2, re
import numpy as np
import base64
import time
import csv
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from paddleocr import PaddleOCR
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup

def initialize_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.page_load_strategy = 'eager'
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
def easyocr_text(image_path):
    original_image = Image.open(image_path).convert("RGBA")
    white_background = Image.new("RGBA", original_image.size, (255, 255, 255, 255))
    combined_image = Image.alpha_composite(white_background, original_image)
    rgb_image = combined_image.convert("RGB")
    rgb_image_np = np.array(rgb_image)
    gray_image = cv2.cvtColor(rgb_image_np, cv2.COLOR_RGB2GRAY)
    _, binary_image = cv2.threshold(gray_image, 200, 255, cv2.THRESH_BINARY_INV)
    binary_image_rgb = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2RGB)
    cv2.imwrite('./test_images/preprocessed.jpg', binary_image)
    #Performing OCR
    reader = easyocr.Reader(['en'])
    result = reader.readtext(binary_image_rgb)
    text_output = ""
    for detection in result:
        text_output += detection[1].replace(" ", "") 
    text_output = re.sub(r'[^A-Za-z0-9]', '', text_output)
    data = 1
    return text_output

def paddleocr_text(image_path):
    original_image = Image.open(BytesIO(image_path)).convert("RGBA")
    white_background = Image.new("RGBA", original_image.size, (255, 255, 255, 255))
    combined_image = Image.alpha_composite(white_background, original_image)
    rgb_image = combined_image.convert("RGB")
    rgb_image_np = np.array(rgb_image)
    gray_image = cv2.cvtColor(rgb_image_np, cv2.COLOR_RGB2GRAY)
    _, binary_image = cv2.threshold(gray_image, 200, 255, cv2.THRESH_BINARY_INV)
    binary_image_rgb = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2RGB)
    
    ocr = PaddleOCR(use_angle_cls=True, lang='en')  
    result = ocr.ocr(binary_image_rgb, cls=True)
    text_output=""
    
    for line in result:
        for detection in line:
            text_output += detection[1][0].replace(" ", "")

    clean_text = re.sub(r'[^A-Za-z0-9]', '', text_output)
    return clean_text

def decode_captcha_image(img_path):
    text = easyocr_text(img_path)
    print(text)
    return text

def fill_captcha(driver,text,field_id):
    captcha_field = driver.find_element(By.ID, field_id)
    submit_btn = driver.find_element(By.ID,'actionFetchDetails')
    captcha_field.send_keys(text)
    time.sleep(3)
    submit_btn.click()
    time.sleep(3)
    
    WebDriverWait(driver, 15).until(
        EC.url_changes(driver.current_url)
    )
    print(driver.page_source)

def select_captcha(org_url,save_path):
    response = requests.get(org_url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    divv = soup.find('div',class_= 'card-body')
    captcha_img = divv.find('img', id='captchaImageId')
    if captcha_img:
            captcha_src = captcha_img.get('src')    
            final_src = 'https://lgdirectory.gov.in/'+str(captcha_src)
            print('https://lgdirectory.gov.in/'+str(captcha_src)) #to check captcha image
            text = fetch_and_save_captcha(final_src,save_path)        
            return text

def fetch_and_save_captcha(captcha_url, save_path):
    try:
        # Make an HTTP request to fetch the CAPTCHA image
        response = requests.get(captcha_url)
        response.raise_for_status()  # Ensure we notice bad responses

        image = Image.open(BytesIO(response.content))
        image.save(save_path)  # Save the image to a file
        print(f"CAPTCHA image saved as {save_path}")
        text = decode_captcha_image('captcha1.jpeg')
        return text
    except Exception as e:
        print(f"Failed to fetch or save CAPTCHA image: {e}")

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
    text = select_captcha(base_url,'captcha1.jpeg')
    fill_captcha(driver,text,'captchaAnswer')
    
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
