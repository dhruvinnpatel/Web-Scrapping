import requests
import os
import easyocr
import re
import time
import json
import pdfkit
import shutil
from PIL import Image
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def init_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "printing.print_preview_sticky_settings.appState": '{"recentDestinations":[{"id":"Save as PDF","origin":"local","account":""}],"selectedDestinationId":"Save as PDF","version":2}',
        "savefile.default_directory": os.path.join(os.getcwd(), "downloaded_pdfs"),  # Set the download directory
        "plugins.always_open_pdf_externally": True,  # Prevent Chrome from opening PDFs in the browser
        "download.default_directory": os.path.join(os.getcwd(), "downloaded_pdfs"),  # Ensure downloads go here
        "download.prompt_for_download": False,  # Don't prompt for download
        "download.directory_upgrade": True  # Allow changing download directory
    })
    chrome_options.add_argument("--kiosk-printing")  # Enable kiosk printing mode
    # chrome_options.add_argument("--headless")  # Uncomment if you want to run in headless mode
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def capture_captcha_image(driver, captcha_img_id, screenshot_path):
    captcha_img = driver.find_element(By.ID, captcha_img_id)
    location = captcha_img.location
    size = captcha_img.size
    driver.save_screenshot('cppp_full.png')

    screenshot = Image.open('cppp_full.png')
    left = location['x']
    top = location['y']
    right = left + size['width']
    bottom = top + size['height']
    captcha_image = screenshot.crop((left, top, right, bottom))
    captcha_image.save(screenshot_path)

def get_home(driver):    
    base_url = "https://eprocure.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page"
    driver.get(base_url)
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'table'))
    )

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'id': 'table'})
    data = []    
    if table:
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            
            if len(tds) >= 3:
                number_of_tenders_text = tds[2].text.strip()
                name = tds[1].text.strip()
                link_tag = tds[2].find('a')
                link = link_tag['href'] if link_tag else None
                
                number_of_tenders = 0
                
                if number_of_tenders_text.isdigit():
                    number_of_tenders = int(number_of_tenders_text)
                
                if link:
                    full_link = "https://eprocure.gov.in" + link
                    data.append({
                        'Number of Tenders': number_of_tenders,
                        'Name': name,
                        'Link': full_link
                    })
    return data

def scrape_tenders(driver, org_url,save_dir):
    tender_data = []
    while True:
        driver.get(org_url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'table'))
        )
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        tender_table = soup.find('table', {'id': 'table'})
        
        if tender_table:
            rows = tender_table.find_all('tr')
            for row in rows[1:]:
                tds = row.find_all('td')
                if len(tds) >= 6:
                    number = tds[0].text.strip()
                    published = tds[1].text.strip()
                    closing = tds[2].text.strip()
                    opening = tds[3].text.strip()
                    title = tds[4].text.strip()
                    org = tds[5].text.strip()
                    amount = tds[6].text.strip()
                    link_tag = tds[4].find('a')
                    link = link_tag['href'] if link_tag else None
                    
                    tender_data.append({
                        'ID':number,
                        'Name': title,
                        'Organization': org,
                        'Published Date': published,
                        'Closing Date': closing,
                        'Opening Date': opening,
                        'Amount': amount,
                        'Link': requests.compat.urljoin(org_url, link) if link else None
                    })
                    # with open('tenders_data.json', 'w') as f:
                    #     json.dump(tender_data, f, indent=4)

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'a#loadNext')  
            if next_button.is_displayed() and next_button.is_enabled():
                next_button.click()
                time.sleep(2)  
            else:
                break  
        except Exception as e:
            print(f"Exception while navigating to the next page: {e}")
            break  

        for tender in tender_data:
                        if tender.get('Link'):  
                            scrape_pdf(driver,tender['Link'], save_dir,tender['ID'])
    
    return tender_data

# def download_pdf(pdf_url, save_dir,tid):
#     os.makedirs(save_dir, exist_ok=True)
#     response = requests.get(pdf_url, stream=True)
    
#     if response.status_code == 200:
#         pdf_path = os.path.join(save_dir, f"{tid}.pdf")
#         with open(pdf_path, 'wb') as f:
#             for chunk in response.iter_content(chunk_size=8192):
#                 f.write(chunk)
#         print(f"PDF saved as {pdf_path}")
#     else:
#         print(f"Failed to download PDF from {pdf_url}. Status code: {response.status_code}")

def scrape_pdf(driver, pdfpage_url, save_dir, tid):
    os.makedirs(save_dir, exist_ok=True)

    # Define the expected filename for the PDF
    new_pdf_path = os.path.join(save_dir, f"tender_{tid}.pdf")

    # Check if the PDF already exists in the save directory
    if os.path.exists(new_pdf_path):
        print(f"PDF for tender {tid} already exists: {new_pdf_path}")
        return  # Skip downloading if it already exists

    # Navigate to the PDF page and wait for content to load
    driver.get(pdfpage_url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'page_content'))
    )

    # Trigger the print dialog
    driver.execute_script('window.print();')  # This should open the print dialog


def select_captcha(driver, captcha_img_id, screenshot_path):
    capture_captcha_image(driver, captcha_img_id, screenshot_path)
    text = ocr_text_from_screenshot(screenshot_path)
    return text.upper()

def ocr_text_from_screenshot(image_path):
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image_path)
    text_output = ""
    for detection in result:
        text_output += detection[1].replace(" ", "")
    clean_text = re.sub(r'[^A-Za-z0-9]', '', text_output)
    return clean_text

def fill_captcha(driver, text, field_id):
    captcha_field = driver.find_element(By.ID, field_id)
    submit_btn = driver.find_element(By.ID, 'Submit')
    captcha_field.clear()
    captcha_field.send_keys(text)
    time.sleep(1)
    submit_btn.click()

def process_state(driver, base_url,dir, max_retries=3):
    attempt = 0
    while attempt < max_retries:
        try:
            captcha_text = select_captcha(driver, 'captchaImage', 'cppp.png')
            print(f"CAPTCHA: {captcha_text}")
            fill_captcha(driver, captcha_text, 'captchaText')
            data = scrape_tenders(driver, base_url,dir)
            time.sleep(4)  # Allow time for data processing
            return data # Exit the function if successful
        except Exception as e:
            attempt += 1
            time.sleep(3)

def main():
    driver = init_driver()
    save_dir = os.path.join(os.getcwd(), "downloaded_pdfs")  # Specify download directory
    os.makedirs(save_dir, exist_ok=True)
    base_url = 'https://eprocure.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page'
    
    try:
        driver.get(base_url)
        data = process_state(driver, base_url, save_dir)
    finally:
        driver.quit()

if __name__ == '__main__':
    main()


