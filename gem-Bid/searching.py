from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

class BidCardExtractor:
    def __init__(self, driver_path, url, output_file):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")  # For headless mode performance
        chrome_options.add_argument("--no-sandbox")  # Additional performance option
        chrome_options.add_argument("--disable-dev-shm-usage")  # Additional performance option
        chrome_options.page_load_strategy = 'eager'
        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.url = url
        self.output_file = output_file
        self.record_summary_printed = False
        self.total_records = None

    def open_webpage(self):
        self.driver.get(self.url)

    def search_bid(self, search_keyword):
        try:
            search_box = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.ID, 'searchBid'))
            )
            search_box.clear()
            search_box.send_keys(search_keyword)
            search_box.send_keys(u'\ue007')

            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card"))
            )
        except Exception as e:
            self._print_and_write(f"An error occurred during the search: {e}")

    def get_brief_item_details(self, card):
        try:
            item_detail_elements = card.find_elements(By.CSS_SELECTOR, "div.col-md-4 a[data-content]")
            if item_detail_elements:
                return [element.get_attribute("data-content").strip() for element in item_detail_elements]
            else:
                item_text = card.find_element(By.CSS_SELECTOR, "div.col-md-4 div:nth-of-type(1)").text.strip()
                return [item_text]
        except Exception as e:
            self._print_and_write(f"Error occurred while getting brief item details: {e}")
            return []

    def extract_record_summary(self):
        try:
            summary_element = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".totalRecord span"))
            )
            summary_text = summary_element.text
            match = re.search(r'of (\d+) records', summary_text)
            if match:
                self.total_records = int(match.group(1))
                return self.total_records
            else:
                self._print_and_write("Could not extract the total number of records.")
                return None
        except Exception as e:
            self._print_and_write(f"An error occurred while extracting the record summary: {e}")
            return None

    def open_output_file(self):
        self.file = open(self.output_file, 'w', encoding='utf-8')

    def _print_and_write(self, text):
        print(text)
        if hasattr(self, 'file'):
            self.file.write(text + '\n')

    def close_output_file(self):
        if hasattr(self, 'file'):
            self.file.close()

    def extract_and_print_cards(self):
        total_card_count = 0
        processed_card_count = 0
        failed_pages_count = 0
        max_failed_pages = 2

        while True:
            try:
                if not self.record_summary_printed:
                    record_summary = self.extract_record_summary()
                    if record_summary is not None:
                        self._print_and_write(f"Total Records: {record_summary}")
                        self.record_summary_printed = True

                try:
                    cards = WebDriverWait(self.driver, 30).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card"))
                    )
                    if not cards:
                        self._print_and_write("No cards found on this page.")
                        failed_pages_count += 1
                        if failed_pages_count >= max_failed_pages:
                            self._print_and_write("Skipped multiple pages due to loading errors.")
                            break
                        continue
                    failed_pages_count = 0

                    page_card_count = len(cards)
                    start_card_number = total_card_count + 1

                    for index, card in enumerate(cards):
                        current_card_number = start_card_number + index
                        self._print_and_write(f"Id: {current_card_number}:")
                        self._print_and_write("-" * 100)

                        try:
                            item_details = self.get_brief_item_details(card)
                            bid_elements = card.find_elements(By.CSS_SELECTOR, "p.bid_no.pull-left a.bid_no_hover")

                            if not bid_elements:
                                continue

                            bid_no_element = bid_elements[0]
                            ra_no_element = bid_elements[1] if len(bid_elements) > 1 else None

                            bid_no_text = bid_no_element.text.strip()
                            bid_no_href = bid_no_element.get_attribute("href")

                            ra_no_text = ra_no_element.text.strip() if ra_no_element else None
                            ra_no_href = ra_no_element.get_attribute("href") if ra_no_element else None

                            quantity_element = card.find_element(By.CSS_SELECTOR, "div.col-md-4 div:nth-of-type(2)")
                            quantity = quantity_element.text.split(":", 1)[-1].strip()

                            department_element = card.find_element(By.CSS_SELECTOR, "div.col-md-5 div:nth-of-type(2)")
                            department_lines = department_element.text.strip().split("\n")
                            department = ", ".join(department_lines)

                            start_date_element = card.find_element(By.CSS_SELECTOR, "div.col-md-3 .start_date")
                            start_date = start_date_element.text.strip()

                            end_date_element = card.find_element(By.CSS_SELECTOR, "div.col-md-3 .end_date")
                            end_date = end_date_element.text.strip()

                            self._print_and_write(f"  BID NO: {bid_no_text}")
                            self._print_and_write(f"  BID NO Link: {bid_no_href}")
                            if ra_no_text:
                                self._print_and_write(f"  RA No.: {ra_no_text}")
                                self._print_and_write(f"  RA No. Link: {ra_no_href}")
                            self._print_and_write(f"  Items: {', '.join(item_details)}")
                            self._print_and_write(f"  Quantity: {quantity}")
                            self._print_and_write(f"  Department Name and Address: {department}")
                            self._print_and_write(f"  Start Date: {start_date}")
                            self._print_and_write(f"  End Date: {end_date}")
                            self._print_and_write("-" * 100)

                            processed_card_count += 1

                            if self.total_records is not None and processed_card_count >= self.total_records:
                                self._print_and_write("All records have been successfully extracted.")
                                return

                        except Exception as card_error:
                            self._print_and_write(f"  Error extracting data for card {current_card_number}: {card_error}")

                    total_card_count += page_card_count

                    try:
                        next_button = WebDriverWait(self.driver, 30).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.page-link.next"))
                        )

                        if "disabled" in next_button.get_attribute("class"):
                            self._print_and_write("No more pages.")
                            break

                        self.driver.execute_script("arguments[0].click();", next_button)
                        WebDriverWait(self.driver, 30).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card"))
                        )

                    except Exception as nav_error:
                        self._print_and_write(f"Error navigating to the next page: {nav_error}")
                        failed_pages_count += 1
                        if failed_pages_count >= max_failed_pages:
                            self._print_and_write("Skipped multiple pages due to loading errors.")
                            break

                except Exception as page_error:
                    self._print_and_write(f"An error occurred while extracting cards: {page_error}")
                    failed_pages_count += 1
                    if failed_pages_count >= max_failed_pages:
                        self._print_and_write("Skipped multiple pages due to loading errors.")
                        break

            except Exception as e:
                self._print_and_write(f"An unexpected error occurred: {e}")



    def close(self):
        self.driver.quit()
        self.close_output_file()

if __name__ == "__main__":
    url = "https://bidplus.gem.gov.in/all-bids"  # Update with the actual URL
    driver_path = ChromeDriverManager().install()
    output_file = "output/without_multiprocessing.txt"  # Path to the output file
    extractor = BidCardExtractor(driver_path, url, output_file)
    
    try:
        search_keyword = input("Enter the search keyword: ").strip()  # Get user input
        start_time = time.time()
        extractor.open_webpage()
        extractor.search_bid(search_keyword)
        extractor.open_output_file()  # Open the output file
        extractor.extract_and_print_cards()
        end_time = time.time()  
        elapsed_time = end_time - start_time
        extractor._print_and_write(f"Total elapsed time: {elapsed_time:.2f} seconds")
    finally:
        extractor.close()
