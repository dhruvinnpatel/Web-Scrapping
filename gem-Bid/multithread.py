from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time

lock = Lock()   
processed_bids = set()
card_counter = 0

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.page_load_strategy = 'eager'
def create_driver():
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def process_page(url):
    local_driver = create_driver()
    local_driver.get(url)
    wait = WebDriverWait(local_driver, 150)
    local_processed_bids = set()

    global card_counter

    try:
        while True:
            try:
                cards = WebDriverWait(local_driver, 100).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card"))
                )
                
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
                        
                        with lock:
                            if unique_bid_id in processed_bids:
                                continue
                            processed_bids.add(unique_bid_id)
                            card_number = card_counter
                            card_counter += 1
                        
                        output = (
                            f"Card Number: {card_number}\n"
                            f"{card.text.strip()}\n"
                            f"Bid No.: {bid_no_text} Link: {bid_no_href}\n"
                        )
                        
                        if ra_no_text:
                            output += f"RA No.: {ra_no_text} Link: {ra_no_href}\n"
                        
                        output += "-" * 100
                        
                        print(output)
                        
                    except Exception as e:
                        print(f"Error processing card: {e}")
                        continue
                
                try:
                    next_button = local_driver.find_element(By.CSS_SELECTOR, "a.page-link.next")
                    
                    if "disabled" in next_button.get_attribute("class"):
                        break
                    
                    next_button.click()
                    
                    WebDriverWait(local_driver, 50).until(
                        EC.staleness_of(cards[0])
                    )
                    
                except Exception as e:
                    print(f"Error navigating to the next page: {e}")
                    break
                
            except Exception as e:
                print(f"Error loading cards: {e}")
                break

    finally:
        local_driver.quit()

def scraper(base_url, num_threads):
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(process_page, base_url) for _ in range(num_threads)]
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Thread error: {e}")

if __name__ == "__main__":
    base_url = "https://bidplus.gem.gov.in/all-bids"
    num_threads = 10
    start_time = time.time()
    scraper(base_url, num_threads)
    print(f"Data collection completed in {time.time() - start_time:.2f} seconds")
    print(f"Total number of unique cards processed: {card_counter}")
