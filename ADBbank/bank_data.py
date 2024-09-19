import os
import time
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

def init_driver(download_dir):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--kiosk-printing")

    # Set the download directory
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def scroll_to_next_button(driver):
    next_button = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'li.pager__item--next a'))
    )
    driver.execute_script("arguments[0].scrollIntoView();", next_button)

def get_data(driver):
    entry_counter = 1
    base_download_dir = os.path.join(os.getcwd(), 'tender_pdfs')
    os.makedirs(base_download_dir, exist_ok=True)

    with open('tender_data.txt', 'w') as file:
        while True:
            try:
                lists = WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, 'list'))
                )
                items = WebDriverWait(lists, 20).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.item.linked'))
                )

                for item in items:
                    try:
                        # Gather all required data in one go
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

                        data = (
                            f"Id: {entry_counter}\n"
                            f"Title: {title}\n"
                            f"Link: {link}\n"
                            f"Status: {status}\n"
                            f"Deadline: {deadline}\n"
                            f"Summary: {summary}\n"
                            f"Notice Type: {notice_type if notice_type else 'N/A'}\n"
                            f"Approval Number: {approval_number if approval_number else 'N/A'}\n"
                            + "=" * 100 + "\n"
                        )
                        file.write(data)
                        print(data)

                        folder_name = os.path.join(base_download_dir, f"tender_pdfs")
                        os.makedirs(folder_name, exist_ok=True)

                        # Scroll to the item before clicking
                        driver.execute_script("arguments[0].scrollIntoView();", item)
                        time.sleep(1)

                        # Click on the link to open the entry
                        item.find_element(By.CSS_SELECTOR, 'div.item-title a').click()
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.TAG_NAME, 'body'))
                        )

                        # Trigger the print dialog
                        driver.execute_script("window.print();")
                        time.sleep(5)  # Wait for the print dialog

                        # Wait for the PDF to download
                        time.sleep(5)

                        # Move the latest downloaded PDF
                        downloads_folder = os.path.expanduser('~/Downloads')
                        pdf_files = [f for f in os.listdir(downloads_folder) if f.endswith('.pdf')]
                        if pdf_files:
                            latest_pdf = max([os.path.join(downloads_folder, f) for f in pdf_files], key=os.path.getctime)
                            new_pdf_path = os.path.join(folder_name, f"tender_{entry_counter}.pdf")
                            shutil.move(latest_pdf, new_pdf_path)
                            print(f"Moved PDF to {new_pdf_path}")
                        else:
                            print(f"PDF for entry {entry_counter} did not download.")
                            continue  # Skip to the next item

                        entry_counter += 1
                        time.sleep(2)
                        driver.back()
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CLASS_NAME, 'list'))
                        )

                    except Exception as e:
                        print(f"An error occurred while processing an item: {e}")

                scroll_to_next_button(driver)

                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, 'li.pager__item--next a')
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(2)
                    else:
                        print("Next button is not enabled, stopping.")
                        break
                except Exception as e:
                    print("No more pages to navigate or error occurred:", e)
                    break

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
