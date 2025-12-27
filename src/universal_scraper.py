import time
import csv
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
TARGET_GROUPS = [
    "https://groups.google.com/g/carbondioxideremoval",
    # Add other groups here later: "https://groups.google.com/g/pangeo", etc.
]
MAX_THREADS_TO_SCRAPE = 5  # Set to 5 for testing, increase to 100+ later
OUTPUT_FILE = "google_group_data.csv"

def setup_driver():
    """Creates a 'Headless' Chrome Browser (invisible to you)"""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment this line to run invisibly later
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # This helps avoid detection
    options.add_argument('--disable-blink-features=AutomationControlled') 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def scrape_group(driver, group_url):
    print(f"\n--- Accessing Group: {group_url} ---")
    driver.get(group_url)
    time.sleep(5) # Wait for page to load

    # 1. Find all conversation rows on the main page
    # Google uses generic class names. 'F0XO1b' is often the container for the row.
    # If this breaks, we inspect the page and update the class name.
    # Strategy: Find all links that look like a thread link.
    
    threads_data = []
    
    # This grabs all elements that are "Generic Conversation Rows"
    # We look for links inside the main role="main" area
    rows = driver.find_elements(By.CSS_SELECTOR, "div[role='listitem']")
    
    print(f"Found {len(rows)} threads on current page. Scraping the top {MAX_THREADS_TO_SCRAPE}...")

    for i, row in enumerate(rows):
        if i >= MAX_THREADS_TO_SCRAPE:
            break
            
        try:
            # Extract basic info from the list view
            # Note: These class names (zX2W9c, etc.) are standard Google Groups classes
            # They MIGHT change over time, but usually stay stable for months.
            
            # The Title is usually the primary text in the row
            title_element = row.find_element(By.CSS_SELECTOR, "div.HzV7m-bN97Pc") 
            title = title_element.text.split("\n")[0] # Grab first line only
            
            # The Link is often on the parent or nearby. 
            # Reliable fallback: Click it, get URL, go back? Too slow.
            # Better: Find the <a> tag inside this row.
            link_element = row.find_element(By.TAG_NAME, "a")
            thread_url = link_element.get_attribute("href")
            
            # The Date
            date_element = row.find_element(By.CSS_SELECTOR, "span.zX2W9c")
            date = date_element.text

            print(f"[{i+1}] Found: {title}")
            
            threads_data.append({
                "group_url": group_url,
                "title": title,
                "date": date,
                "url": thread_url
            })
            
        except Exception as e:
            print(f"Skipping row {i}: {e}")
            continue

    return threads_data

def scrape_thread_content(driver, thread_data):
    """Visits the specific thread URL to get the actual conversation text"""
    print(f"   > Fetching content for: {thread_data['title'][:30]}...")
    driver.get(thread_data['url'])
    time.sleep(random.uniform(2, 4)) # Human-like pause
    
    try:
        # The message bodies are usually in 'div.GbH70b' or similar
        # We just grab all text from the main message container
        main_content = driver.find_element(By.CSS_SELECTOR, "div[role='main']")
        full_text = main_content.text
        return full_text
    except Exception as e:
        print(f"   > Error reading content: {e}")
        return "Error extracting text"

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    driver = setup_driver()
    all_records = []

    try:
        # Step 1: get the list of threads
        for group in TARGET_GROUPS:
            threads = scrape_group(driver, group)
            
            # Step 2: Go into each thread and get the text
            for thread in threads:
                content = scrape_thread_content(driver, thread)
                thread['content'] = content
                all_records.append(thread)
                
                # IMPORTANT: Wait between requests to avoid IP Ban
                time.sleep(random.uniform(3, 6))

        # Step 3: Save to CSV
        keys = all_records[0].keys()
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_records)
            
        print(f"\nSUCCESS: Scraped {len(all_records)} conversations. Saved to {OUTPUT_FILE}")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        driver.quit()