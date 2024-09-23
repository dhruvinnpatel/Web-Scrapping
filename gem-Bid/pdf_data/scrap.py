import os
import time
import multiprocessing
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# Setup Chrome options
def create_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Uncomment for headless mode
    chrome_options.page_load_strategy = 'eager'
    prefs = {
        "download.default_directory": os.getcwd(),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def download_pdf(url_folder):
    url, folder_name = url_folder
    driver = create_driver()
    try:
        driver.get(url)
        time.sleep(5)  # Allow time for the PDF to load/download

        # Wait for the PDF to be downloaded
        download_path = os.getcwd()  # Current working directory for downloads
        filename = None

        # Check for downloaded files in the directory
        while True:
            for f in os.listdir(download_path):
                if f.endswith('.pdf'):
                    filename = f
                    break

            if filename:
                break

            time.sleep(1)  # Wait a bit before checking again

        # Move the downloaded file to the designated folder
        if filename:
            os.makedirs(folder_name, exist_ok=True)
            os.rename(os.path.join(download_path, filename), os.path.join(folder_name, filename))
            print(f"Downloaded {filename} to {folder_name}")
        else:
            print(f"No PDF downloaded from {url}")

    finally:
        driver.quit()

def safe_find_elements(driver, by, value, max_retries=3):
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
            driver = create_driver()
            driver.get("https://bidplus.gem.gov.in/all-bids")

            processed_bids = set()
            card_index = 1

            while True:
                print(f"Processing page for Entry {card_index}")
                try:
                    # Wait for cards to be present
                    cards = safe_find_elements(driver, By.CSS_SELECTOR, ".card")
                    if not cards:
                        print("No cards found on this page.")
                        break

                    for card in cards:
                        try:
                            bid_elements = card.find_elements(By.CSS_SELECTOR, ".bid_no_hover")
                            if not bid_elements:
                                print("No bid elements found for this card.")
                                continue

                            bid_no_element = bid_elements[0]
                            ra_no_element = bid_elements[1] if len(bid_elements) > 1 else None

                            bid_no_text = bid_no_element.text.strip()
                            bid_no_href = bid_no_element.get_attribute("href")

                            ra_no_text = ra_no_element.text.strip() if ra_no_element else None
                            ra_no_href = ra_no_element.get_attribute("href") if ra_no_element else None

                            unique_bid_id = (bid_no_text, ra_no_text if ra_no_text else "")
                            if unique_bid_id in processed_bids:
                                print(f"Bid already processed: {unique_bid_id}")
                                continue

                            processed_bids.add(unique_bid_id)

                            # Use a consistent folder name for both Bid and RA
                            folder_name = os.path.join(main_pdf_directory, f"Entry_{card_index}")

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

                            # Start PDF download in a separate process
                            processes = []
                            if bid_no_href:
                                bid_process = multiprocessing.Process(target=download_pdf, args=((bid_no_href, folder_name),))
                                bid_process.start()
                                processes.append(bid_process)

                            if ra_no_href:
                                ra_process = multiprocessing.Process(target=download_pdf, args=((ra_no_href, folder_name),))
                                ra_process.start()
                                processes.append(ra_process)

                            # Ensure all download processes finish before continuing
                            for process in processes:
                                process.join()

                            card_index += 1

                        except Exception as e:
                            print(f"Error processing card: {e}")
                            continue

                    # Navigate to the next page
                    for attempt in range(3):  # Retry logic for navigating to the next page
                        try:
                            print("Attempting to find the next page button...")
                            next_button = safe_find_elements(driver, By.CSS_SELECTOR, "a.page-link.next")[0]

                            if "disabled" in next_button.get_attribute("class"):
                                print("No more pages.")
                                return  # Exit the loop if there are no more pages

                            next_button.click()
                            print("Clicked on the next page button. Waiting for the next page to load...")

                            # Wait for a specific element on the new page to ensure it’s fully loaded
                            WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card")))
                            print("Next page loaded successfully.")
                            break  # Exit the retry loop if successful
                        except Exception as e:
                            print(f"Attempt {attempt + 1} failed: {e}")
                            if attempt == 2:  # Last attempt
                                print("Failed to navigate to the next page after multiple attempts.")
                                return  # Exit the loop if all attempts fail

                except Exception as e:
                    print(f"Error loading cards: {e}")
                    break

        finally:
            driver.quit()


if __name__ == "__main__":
    scraper()
