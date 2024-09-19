import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.page_load_strategy = 'eager'
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def write_to_file(file, data):
    with open(file, 'a', encoding='utf-8') as f:
        f.write(data + "\n" + "-" * 100 + "\n")

def get_data(driver):
    id_counter = 1
    file = 'data.txt'
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write("Data Collection\n")
        f.write("=" * 100 + "\n")
    
    while True:
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))

            tbody = driver.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")

            if rows:
                for row in rows:
                    try:
                        data = row.find_elements(By.TAG_NAME, "td")
                        if len(data) == 6:
                            description = data[0].text
                            description_link = data[0].find_element(By.TAG_NAME, "a").get_attribute("href") if data[0].find_elements(By.TAG_NAME, "a") else None

                            country = data[1].text
                            project_title = data[2].text
                            project_link = data[2].find_element(By.TAG_NAME, "a").get_attribute("href") if data[2].find_elements(By.TAG_NAME, "a") else None

                            notice_type = data[3].text
                            language = data[4].text
                            published_date = data[5].text
                            
                            # Format data
                            formatted_data = (
                                f"ID: {id_counter}\n"
                                f"Description: {description}\n"
                                f"Description Link: {description_link if description_link else 'N/A'}\n"
                                f"Country: {country}\n"
                                f"Project Title: {project_title}\n"
                                f"Project Link: {project_link if project_link else 'N/A'}\n"
                                f"Notice Type: {notice_type}\n"
                                f"Language: {language}\n"
                                f"Published Date: {published_date}"
                            )
                            print(formatted_data)
                            write_to_file(file, formatted_data)
                            
                            id_counter += 1
                    except Exception as e:
                        print(f"An error occurred while processing a row: {e}")
                        traceback.print_exc()

            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.pagination li a i.fa-angle-right"))
                )
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(20)  # Small delay to ensure the page has time to load
            except Exception as e:
                print(f"No more pages or an error occurred: {e}")
                break  # Exit loop if no more pages
            
        except Exception as e:
            print(f"An error occurred while processing the page: {e}")
            traceback.print_exc()
            break

def main():
    driver = init_driver()
    try:
        driver.get("https://projects.worldbank.org/en/projects-operations/procurement?srce=both")
        get_data(driver)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
