import os
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# Setup Chrome options
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Uncomment for headless mode
chrome_options.page_load_strategy = 'normal'
prefs = {
    "download.default_directory": os.getcwd(),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

def download_pdf(url, folder_name):
    driver.get(url)
    time.sleep(2)  # Shortened wait for the PDF to load/download

    # Wait for the PDF to be downloaded
    download_path = os.getcwd()  # Current working directory for downloads
    filename = None

    while True:
        # Check for downloaded files in the directory
        for f in os.listdir(download_path):
            if f.endswith('.pdf'):
                filename = f
                break

        if filename:
            break

        time.sleep(1)  # Wait a bit before checking again

    # Move the downloaded file to the designated folder
    os.rename(os.path.join(download_path, filename), os.path.join(folder_name, filename))

def threaded_download(url, folder_name):
    thread = threading.Thread(target=download_pdf, args=(url, folder_name))
    thread.start()
    return thread

def safe_find_elements(by, value, max_retries=3):
    for attempt in range(max_retries):
        try:
            return WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((by, value)))
        except StaleElementReferenceException:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retrying
                continue
            else:
                raise  # Raise if the last attempt fails

def scraper():
    main_pdf_directory = "pdfs"
    os.makedirs(main_pdf_directory, exist_ok=True)

    with open("data.txt", "w", encoding="utf-8") as output_file:
        try:
            driver.get("https://bidplus.gem.gov.in/all-bids")

            processed_bids = set()
            card_index = 1

            while True:
                try:
                    # Wait for cards to be present
                    cards = safe_find_elements(By.CSS_SELECTOR, ".card")

                    for card in cards:
                        try:
                            bid_elements = card.find_elements(By.CSS_SELECTOR, ".bid_no_hover")
                            if not bid_elements:
                                continue

                            bid_no_element = bid_elements[0]
                            ra_no_element = bid_elements[1] if len(bid_elements) > 1 else None

                            bid_no_text = bid_no_element.text.strip()
                            bid_no_href = bid_no_element.get_attribute("href")

                            ra_no_text = ra_no_element.text.strip() if ra_no_element else None
                            ra_no_href = ra_no_element.get_attribute("href") if ra_no_element else None

                            unique_bid_id = (bid_no_text, ra_no_text if ra_no_text else "")
                            if unique_bid_id in processed_bids:
                                continue

                            processed_bids.add(unique_bid_id)

                            folder_name = os.path.join(main_pdf_directory, f"Entry_{card_index}")
                            os.makedirs(folder_name, exist_ok=True)

                            output = (
                                f"Id: {card_index}\n"
                                f"{card.text.strip()}\n"
                                f"Bid No.: {bid_no_text} Link: {bid_no_href}\n"
                            )

                            if ra_no_text:
                                output += f"RA No.: {ra_no_text} Link: {ra_no_href}\n"

                            output += "-" * 100 + "\n"
                            output_file.write(output)
                            print(output)

                            # Start PDF downloads in separate threads
                            threads = []
                            threads.append(threaded_download(bid_no_href, folder_name))
                            if ra_no_href:
                                threads.append(threaded_download(ra_no_href, folder_name))

                            for thread in threads:
                                thread.join()  # Wait for all downloads to finish

                            card_index += 1

                        except Exception as e:
                            print(f"Error processing card: {e}")
                            continue

                    # Navigate to next page
                    try:
                        next_button = safe_find_elements(By.CSS_SELECTOR, "a.page-link.next")[0]

                        if "disabled" in next_button.get_attribute("class"):
                            print("No more pages.")
                            break

                        next_button.click()
                        WebDriverWait(driver, 50).until(EC.staleness_of(cards[0]))

                    except Exception as e:
                        print(f"Error navigating to the next page: {e}")
                        break

                except Exception as e:
                    print(f"Error loading cards: {e}")
                    break

        finally:
            driver.quit()

if __name__ == "__main__":
    scraper()
