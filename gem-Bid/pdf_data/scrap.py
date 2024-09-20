import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Setup Chrome options
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Uncomment for headless mode
chrome_options.page_load_strategy = 'eager'
prefs = {
    "download.default_directory": os.getcwd(),  # Set the default download directory
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

def download_pdf(url, folder_name):
    # Ensure the folder exists
    os.makedirs(folder_name, exist_ok=True)
    
    # Download the PDF
    driver.get(url)
    time.sleep(5)  # Wait for the PDF to load/download

    # Move the downloaded file to the designated folder
    for filename in os.listdir(os.getcwd()):
        if filename.endswith('.pdf'):
            os.rename(os.path.join(os.getcwd(), filename), os.path.join(folder_name, filename))
            break  # Move only the first PDF downloaded

def scraper():
    main_pdf_directory = "pdfs"
    os.makedirs(main_pdf_directory, exist_ok=True)

    # Create a data.txt file to save output
    with open("data.txt", "w", encoding="utf-8") as output_file:
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

                            # Create a folder for the current card_index within the main PDF directory
                            folder_name = os.path.join(main_pdf_directory, f"Entry_{card_index}")
                            
                            # Print information about the bid
                            output = (
                                f"Id: {card_index}\n"
                                f"{card.text.strip()}\n"
                                f"Bid No.: {bid_no_text} Link: {bid_no_href}\n"
                            )
                            
                            if ra_no_text:
                                output += f"RA No.: {ra_no_text} Link: {ra_no_href}\n"
                            
                            output += "-" * 100 + "\n"
                            
                            # Write to the data.txt file
                            output_file.write(output)

                            print(output)

                            # Download PDFs
                            download_pdf(bid_no_href, folder_name)
                            if ra_no_href:
                                download_pdf(ra_no_href, folder_name)
                            
                            card_index += 1  

                        except Exception as e:
                            print(f"Error processing card: {e}")
                            continue
                    
                    # Navigate to next page
                    try:
                        next_button = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "a.page-link.next"))
                        )
                        
                        if "disabled" in next_button.get_attribute("class"):
                            print("No more pages.")
                            break
                        
                        next_button.click()
                        
                        # Wait for the page to load new cards
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
