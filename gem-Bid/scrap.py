from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.page_load_strategy = 'eager'

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

def scraper():
    try:
        driver.get("https://bidplus.gem.gov.in/all-bids")

        wait = WebDriverWait(driver, 150)
        processed_bids = set()
        card_index = 1  

        while True:
            try:
                # Wait for cards to be present
                cards = WebDriverWait(driver, 100).until(
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
                        
                        if unique_bid_id in processed_bids:
                            continue
                        
                        processed_bids.add(unique_bid_id)
                        
                        output = (
                            f"Id: {card_index}\n"
                            f"{card.text.strip()}\n"
                            f"Bid No.: {bid_no_text} Link: {bid_no_href}\n"
                        )
                        
                        if ra_no_text:
                            output += f"RA No.: {ra_no_text} Link: {ra_no_href}\n"
                        
                        output += "-" * 100
                        
                        print(output)
                        
                        card_index += 1  

                    except Exception as e:
                        print(f"Error processing card: {e}")
                        continue
                
                # Navigate to next page
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "a.page-link.next")
                    
                    if "disabled" in next_button.get_attribute("class"):
                        print("No more pages.")
                        break
                    
                    next_button.click()
                    
                    WebDriverWait(driver, 50).until(
                        EC.staleness_of(cards[0])
                    )
                    
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