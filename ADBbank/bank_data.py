import os
import time
import shutil
import multiprocessing
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

def init_driver(download_dir):
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--headless")  # Uncomment for headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--kiosk-printing")

    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "printing.print_preview_sticky_settings.appState": "{\"recentDestinations\":[{\"id\":\"Save as PDF\",\"origin\":\"local\",\"account\":\"\"}],\"selectedDestinationId\":\"Save as PDF\",\"version\":2}"
    })

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def wait_for_downloads(download_folder, timeout=60):
    seconds_passed = 0
    while seconds_passed < timeout:
        pdf_files = [f for f in os.listdir(download_folder) if f.endswith('.pdf')]
        if pdf_files:
            return pdf_files
        time.sleep(1)
        seconds_passed += 1
    return []

def download_pdf(entry_counter, entry_data):
    base_download_dir = os.path.join(os.getcwd(), 'tender_pdfs')
    entry_folder = os.path.join(base_download_dir, f"tender_{entry_counter}")
    os.makedirs(entry_folder, exist_ok=True)

    driver = init_driver(entry_folder)
    try:
        driver.get(entry_data['link'])
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        print("Page loaded for entry:", entry_counter)

        driver.execute_script("window.print();")
        
        downloads_folder = os.path.expanduser('~/Downloads')
        pdf_files = wait_for_downloads(downloads_folder)
        
        if pdf_files:
            latest_pdf = max([os.path.join(downloads_folder, f) for f in pdf_files], key=os.path.getctime)
            new_pdf_path = os.path.join(entry_folder, f"tender_{entry_counter}.pdf")
            shutil.move(latest_pdf, new_pdf_path)
            print(f"Moved PDF to {new_pdf_path}")
        else:
            print(f"PDF for entry {entry_counter} did not download.")
    except Exception as e:
        print(f"An error occurred while processing entry {entry_counter}: {e}")
    finally:
        driver.quit()

def get_data(driver):
    global entry_counter
    entry_counter = 1
    base_download_dir = os.path.join(os.getcwd(), 'tender_pdfs')
    os.makedirs(base_download_dir, exist_ok=True)

    while True:
        try:
            lists = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.CLASS_NAME, 'list'))
            )
            items = WebDriverWait(lists, 20).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.item.linked'))
            )

            items_to_process = items[:20]
            entry_data_list = []

            for item in items_to_process:
                if item:
                    try:
                        status = item.find_element(By.XPATH, './/div[span[contains(text(), "Status:")]]/span[2]').text
                        deadline = item.find_element(By.XPATH, './/div[span[contains(text(), "Deadline:")]]/span[2]').text
                        title = item.find_element(By.CLASS_NAME, 'item-title').text
                        link = item.find_element(By.CSS_SELECTOR, 'div.item-title a').get_attribute('href')
                        summary = item.find_element(By.CLASS_NAME, 'item-summary').text

                        notice_type, approval_number = None, None
                        item_details = item.find_elements(By.XPATH, './/div[contains(@class, "item-details")]/p')
                        for detail in item_details:
                            label = detail.find_element(By.TAG_NAME, 'span').text
                            if label == "Notice Type:":
                                notice_type = detail.find_elements(By.TAG_NAME, 'span')[1].text
                            elif label == "Approval Number:":
                                approval_number = detail.find_elements(By.TAG_NAME, 'span')[1].text

                        data = {
                            'id': entry_counter,
                            'title': title,
                            'link': link,
                            'status': status,
                            'deadline': deadline,
                            'summary': summary,
                            'notice_type': notice_type,
                            'approval_number': approval_number
                        }
                        entry_data_list.append(data)

                        entry_counter += 1

                    except Exception as e:
                        print(f"An error occurred while processing an item: {e}")

            with multiprocessing.Pool(processes=10) as pool:
                pool.starmap(download_pdf, [(data['id'], data) for data in entry_data_list])

            # Retry logic for clicking the next button
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "a[rel='next'][title='Go to next page']")
                    driver.execute_script("arguments[0].scrollIntoView();", next_button)
                    
                    WebDriverWait(driver, 20).until(EC.element_to_be_clickable(next_button))
                    
                    driver.execute_script("arguments[0].click();", next_button)
                    break 

                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(1) 
                    if attempt == max_retries - 1:
                        print("Max retries reached. Exiting...")
                        return

        except Exception as e:
            print("Error finding list:", e)
            break

def main():
    base_download_dir = os.path.join(os.getcwd(), 'tender_pdfs')
    driver = init_driver(base_download_dir)
    try:
        driver.get("https://www.adb.org/projects/tenders")
        get_data(driver)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
