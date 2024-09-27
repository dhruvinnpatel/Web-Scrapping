import os
import time
import requests
import logging
import pdfplumber
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
from webdriver_manager.chrome import ChromeDriverManager

def init_driver():
    chrome_options = Options()
    chrome_options.page_load_strategy = 'eager'
    prefs = {
        "download.default_directory": os.getcwd(),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_argument("--headless")
    chrome_options.add_experimental_option("prefs", prefs)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_brief_item_details(card):
    try:
        item_detail_elements = card.find_elements(By.CSS_SELECTOR, "div.col-md-4 a[data-content]")
        item_details = [element.get_attribute("data-content").strip() for element in item_detail_elements]
        return item_details
    except Exception as e:
        print(f"There is no brief item details: {e}")
        return []

def get_current_page_number(driver):
    try:
        wait = WebDriverWait(driver, 120)
        pagination = wait.until(
            EC.presence_of_element_located((By.ID, "light-pagination"))
        )
        page_numbers = pagination.find_elements(By.CSS_SELECTOR, '.current')
        
        for item in page_numbers:
            page_number_text = item.text.strip()
            if page_number_text.isdigit():
                return int(page_number_text)

        print("Current page number not found or is not a digit.")
        return None
    except Exception as e:
        print(f"Error occurred while getting current page number: {e}")
        return None

def download_file(url, save_dir, filename):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, filename)

        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {file_path}")
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")

def extract_and_download_embedded_links(pdf_path, save_dir, bid_no_text=None, ra_no_text=None,
                                        file_extensions=('.pdf', '.xlsx', '.csv', '.ods', '.txt')):
    url_set = set()  
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                links = page.hyperlinks
                for link in links:
                    uri = link.get('uri')
                    if uri and uri.endswith(file_extensions) and uri not in url_set:
                        url_set.add(uri)  # Add the unique link to the set
                        embedded_text = uri.split('/')[-1].split('?')[0]
                        embedded_filename = f"{embedded_text}"
                        
                        # Determine save directory based on the source PDF
                        if bid_no_text:
                            save_dir = os.path.join("Pdf_trial", bid_no_text)
                        elif ra_no_text:
                            save_dir = os.path.join("Pdf_trial", ra_no_text)
                            
                        download_file(uri, save_dir, embedded_filename)  # Download the file
    except Exception as e:
        logging.error(f"Error extracting and downloading embedded links from {pdf_path}: {e}")

def download_pdf(url, folder_name):
    driver = init_driver()
    try:
        driver.get(url)
        time.sleep(5)  # Allow time for the PDF to load/download

        download_path = os.getcwd()
        filename = None

        # Wait for the PDF to be downloaded
        while True:
            for f in os.listdir(download_path):
                if f.endswith('.pdf'):
                    filename = f
                    break

            if filename:
                break

            if driver.current_url != url:
                print(f"Redirected to a different page: {driver.current_url}")
                return

            time.sleep(1)

        # Move the downloaded file to the designated folder
        if filename:
            os.makedirs(folder_name, exist_ok=True)
            pdf_path = os.path.join(download_path, filename)
            os.rename(pdf_path, os.path.join(folder_name, filename))
            print(f"Downloaded {filename} to {folder_name}")

            # Extract links from the downloaded PDF using pdfplumber
            extract_and_download_embedded_links(os.path.join(folder_name, filename), folder_name)

        else:
            print(f"No PDF downloaded from {url}")

    finally:
        driver.quit()

def extract_links_from_list_ra(driver, folder_name):
    try:
        ra_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='showradocumentPdf']")
        for link in ra_links:
            href = link.get_attribute("href")
            print(f"Extracted RA Document Link: {href}")
            download_pdf(href, folder_name)  # Download each RA document directly into the entry folder
    except Exception as e:
        print(f"Error extracting links from RA page: {e}")

def worker(bid_no_href, ra_no_href, bid_no_text, ra_no_text):
    if bid_no_href:
        download_pdf(bid_no_href, os.path.join("Pdf_trial", bid_no_text))
    if ra_no_href:
        download_pdf(ra_no_href, os.path.join("Pdf_trial", ra_no_text))

def process_pages(start_page, end_page, output_file):
    driver = init_driver()
    processed_bids = set()
    index = 1
    main_pdf_directory = "Pdf_trial"
    os.makedirs(main_pdf_directory, exist_ok=True)

    try:
        for page_num in range(start_page, end_page + 1):
            driver.get("https://bidplus.gem.gov.in/all-bids")
            wait = WebDriverWait(driver, 120)

            current_page_number = get_current_page_number(driver)
            if current_page_number is None:
                print(f"Failed to get page number for page {page_num}")
                continue

            while True:
                try:
                    cards = WebDriverWait(driver, 120).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card"))
                    )

                    with ThreadPoolExecutor() as executor:
                        futures = []
                        for card in cards:
                            try:
                                item_details = get_brief_item_details(card)
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

                                output = (
                                    # f"Page: {current_page_number}\n"
                                    f"Id: {index}\n"
                                    f"{card.text.strip()}\n"
                                    f"Bid No.: {bid_no_text} Link: {bid_no_href}\n"
                                )

                                if ra_no_text:
                                    output += f"RA No.: {ra_no_text} Link: {ra_no_href}\n"

                                output += f"Item Details: {', '.join(item_details)}\n"
                                output += "-" * 100 + "\n"

                                print(output)
                                with open(output_file, "a") as f:
                                    f.write(output)

                                futures.append(executor.submit(worker, bid_no_href, ra_no_href, bid_no_text, ra_no_text))
                                index += 1

                            except Exception as card_error:
                                print(f"Error processing card: {card_error}")

                    for future in as_completed(futures):
                        future.result()

                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, "a.page-link.next")
                        if "disabled" in next_button.get_attribute("class"):
                            print("No more pages.")
                            break
                        next_button.click()
                        WebDriverWait(driver, 120).until(EC.staleness_of(cards[0]))
                        current_page_number = get_current_page_number(driver)
                        if current_page_number is None:
                            print("Failed to get page number after navigating to next page")
                            break

                    except Exception as nav_error:
                        print(f"Error navigating to the next page: {nav_error}")
                        break

                except Exception as load_error:
                    print(f"Error loading cards on page {page_num}: {load_error}")
                    continue

    finally:
        driver.quit()

if __name__ == "__main__":
    start_time = time.time()  
    
    total_pages = 6000  
    output_file = "trial_data.txt"  

    process_pages(1, total_pages, output_file)

    end_time = time.time()  
    elapsed_time = end_time - start_time
    print(f"Total elapsed time: {elapsed_time:.2f} seconds")
