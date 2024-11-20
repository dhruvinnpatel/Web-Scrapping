import traceback
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import multiprocessing
import math

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('start-maximized')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])    
    chrome_options.page_load_strategy = 'eager'
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_brief_item_details(card):
    try:
        item_detail_elements = card.find_elements(By.CSS_SELECTOR, "div.col-md-4 a[data-content]")
        item_details = [element.get_attribute("data-content").strip() for element in item_detail_elements]
        return item_details

    except Exception as e:
        print(f"Error occurred while getting brief item details: {e}")
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

def reload_cards(driver):
    driver.execute_script("window.scrollTo(0, 0);")  # Scroll to the top
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # Scroll to the bottom

def process_pages(start_page, end_page, processed_bids, index_manager, lock, output_file):
    driver = init_driver()
    try:
        for page_num in range(start_page, end_page + 1):
            driver.get(f"https://bidplus.gem.gov.in/all-bids")
            wait = WebDriverWait(driver, 120)
            retry_count = 0

            current_page_number = get_current_page_number(driver)
            if current_page_number is None:
                print(f"Failed to get page number for page {page_num}")
                continue

            while True:
                try:
                    cards = WebDriverWait(driver, 120).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card"))
                    )
                    if not cards:
                        print(f"No cards found on page {page_num}")
                        reload_cards(driver)
                        retry_count += 1
                        if retry_count >= 3:
                            print(f"Skipped multiple pages due to loading errors on page {page_num}.")
                            break
                        continue
                    
                    retry_count = 0
                    
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

                            with lock:
                                if unique_bid_id in processed_bids:
                                    continue

                                processed_bids.append(unique_bid_id)
                                card_index = index_manager.value
                                index_manager.value += 1

                            output = (
                                f"Page: {current_page_number}\n"  
                                f"Id: {card_index}\n"
                                f"{card.text.strip()}\n"
                                f"Bid No.: {bid_no_text} Link: {bid_no_href}\n"
                                f"Item Details: {', '.join(item_details)}\n"
                            )

                            if ra_no_text:
                                output += f"RA No.: {ra_no_text} Link: {ra_no_href}\n"

                            output += "-" * 100 + "\n"

                            print(output)
                            with open(output_file, "a") as f:
                                f.write(output)

                        except Exception as card_error:
                            print(f"Error processing card: {card_error}")
                            continue

                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, "a.page-link.next")

                        if "disabled" in next_button.get_attribute("class"):
                            print("No more pages.")
                            break

                        next_button.click()
                        WebDriverWait(driver, 120).until(
                            EC.staleness_of(cards[0])
                        )

                        current_page_number = get_current_page_number(driver)
                        if current_page_number is None:
                            print(f"Failed to get page number after navigating to next page")
                            break

                    except Exception as nav_error:
                        print(f"Error navigating to the next page: {nav_error}")
                        break

                except Exception as load_error:
                    print(f"Error loading cards on page {page_num}: {load_error}")
                    reload_cards(driver)
                    if retry_count >= 3:
                        print(f"Failed to load cards after 3 attempts")
                        break

    finally:
        driver.quit()


def scraper_worker(start_page, end_page, processed_bids, index_manager, lock, output_file):
    process_pages(start_page, end_page, processed_bids, index_manager, lock, output_file)

if __name__ == "__main__":
    start_time = time.time()  
    
    total_pages = 3656  
    num_workers = 10 
    output_file = "scraped_data.txt"  

    pages_per_worker = math.ceil(total_pages / num_workers)
    ranges = [(i * pages_per_worker + 1, min((i + 1) * pages_per_worker, total_pages)) for i in range(num_workers)]

    with multiprocessing.Manager() as manager:
        processed_bids = manager.list()  
        index_manager = manager.Value('i', 1)  
        lock = manager.Lock()  

        processes = []
        for start_page, end_page in ranges:
            p = multiprocessing.Process(target=scraper_worker, args=(start_page, end_page, processed_bids, index_manager, lock, output_file))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

    end_time = time.time()  
    elapsed_time = end_time - start_time
    print(f"Total elapsed time: {elapsed_time:.2f} seconds")