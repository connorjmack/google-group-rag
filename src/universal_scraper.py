import time
import csv
import random
import json
from pathlib import Path
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import Config
from src.logger import setup_logger

logger = setup_logger("scraper")


class Checkpoint:
    """Manages scraping progress checkpoints for resume capability."""

    def __init__(self, checkpoint_file: str = None):
        self.checkpoint_file = checkpoint_file or Config.CHECKPOINT_FILE
        self.data = self._load()

    def _load(self) -> Dict:
        """Load checkpoint from disk."""
        default_data = {"groups": {}, "scraped_urls": []}
        checkpoint_path = Path(self.checkpoint_file)
        if checkpoint_path.exists():
            with open(checkpoint_path, 'r') as f:
                try:
                    data = json.load(f)
                    # Ensure required keys exist
                    if "groups" not in data:
                        data["groups"] = {}
                    if "scraped_urls" not in data:
                        data["scraped_urls"] = []
                    logger.info(f"Loaded checkpoint from {self.checkpoint_file}")
                    return data
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in checkpoint file, using defaults")
                    return default_data
        return default_data

    def save(self):
        """Save checkpoint to disk."""
        checkpoint_path = Path(self.checkpoint_file)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_path, 'w') as f:
            json.dump(self.data, f, indent=2)
        logger.debug(f"Checkpoint saved to {self.checkpoint_file}")

    def get_last_thread_index(self, group_url: str) -> int:
        """Get the index of the last successfully scraped thread for a group."""
        return self.data["groups"].get(group_url, {}).get("last_thread_index", -1)

    def update_thread_progress(self, group_url: str, thread_index: int):
        """Update the progress for a specific group."""
        if group_url not in self.data["groups"]:
            self.data["groups"][group_url] = {}
        self.data["groups"][group_url]["last_thread_index"] = thread_index
        self.save()

    def is_group_completed(self, group_url: str) -> bool:
        """Check if a group has been fully scraped."""
        return self.data["groups"].get(group_url, {}).get("completed", False)

    def mark_group_completed(self, group_url: str):
        """Mark a group as fully scraped."""
        if group_url not in self.data["groups"]:
            self.data["groups"][group_url] = {}
        self.data["groups"][group_url]["completed"] = True
        self.save()

    def is_url_scraped(self, url: str) -> bool:
        """Check if a URL has already been scraped."""
        if "scraped_urls" not in self.data:
            self.data["scraped_urls"] = []
        return url in self.data["scraped_urls"]

    def mark_url_scraped(self, url: str):
        """Mark a URL as scraped."""
        if "scraped_urls" not in self.data:
            self.data["scraped_urls"] = []
        if url not in self.data["scraped_urls"]:
            self.data["scraped_urls"].append(url)
            self.save()

    def get_scraped_count(self) -> int:
        """Get total number of unique URLs scraped."""
        return len(self.data.get("scraped_urls", []))


class GoogleGroupsScraper:
    """Enhanced scraper with pagination, better extraction, and checkpointing."""

    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else Config.HEADLESS_MODE
        self.driver = None
        self.checkpoint = Checkpoint()

    def setup_driver(self):
        """Creates a Chrome browser with anti-detection measures."""
        logger.info("Setting up Chrome WebDriver...")
        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument('--headless')

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        logger.info("WebDriver setup complete")

    def scroll_to_load_more(self, max_scrolls: int = 10) -> int:
        """
        Scrolls the page to trigger lazy loading of more threads.

        Returns:
            Number of scroll attempts made
        """
        logger.info("Attempting to load more threads via scrolling...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scrolls = 0

        for i in range(max_scrolls):
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3))

            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logger.info(f"No more content to load after {scrolls} scrolls")
                break

            last_height = new_height
            scrolls += 1
            logger.debug(f"Scroll {scrolls}: Page height increased to {new_height}")

        return scrolls

    def navigate_to_next_page(self) -> bool:
        """
        Attempts to click the 'Next' button to load the next page of threads.

        Returns:
            True if successfully navigated to next page, False otherwise
        """
        try:
            # Look for next page button - Google Groups uses various patterns
            next_button_selectors = [
                "//button[@aria-label='Next page']",
                "//button[contains(text(), 'Next')]",
                "//a[contains(@class, 'next')]",
            ]

            for selector in next_button_selectors:
                try:
                    next_button = self.driver.find_element(By.XPATH, selector)
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(Config.PAGE_LOAD_WAIT)
                        logger.info("Navigated to next page")
                        return True
                except NoSuchElementException:
                    continue

            logger.debug("No next page button found")
            return False

        except Exception as e:
            logger.warning(f"Error navigating to next page: {e}")
            return False

    def extract_thread_metadata(self, row, row_index: int) -> Optional[Dict]:
        """
        Extracts metadata from a thread row.

        Args:
            row: Selenium WebElement representing the thread row
            row_index: Index of the row for logging

        Returns:
            Dictionary with thread metadata or None if extraction failed
        """
        try:
            # Title - trying multiple selectors
            title = None
            title_selectors = [
                "div.HzV7m-bN97Pc",
                "div[role='link']",
                "a",
            ]

            for selector in title_selectors:
                try:
                    title_element = row.find_element(By.CSS_SELECTOR, selector)
                    title = title_element.text.split("\n")[0]
                    if title:
                        break
                except NoSuchElementException:
                    continue

            if not title:
                logger.warning(f"Could not extract title from row {row_index}")
                return None

            # URL
            link_element = row.find_element(By.TAG_NAME, "a")
            thread_url = link_element.get_attribute("href")

            # Date
            date = "Unknown"
            date_selectors = ["span.zX2W9c", "span[class*='date']"]
            for selector in date_selectors:
                try:
                    date_element = row.find_element(By.CSS_SELECTOR, selector)
                    date = date_element.text
                    break
                except NoSuchElementException:
                    continue

            # Author - extract if available
            author = "Unknown"
            author_selectors = ["div[class*='author']", "span[class*='author']"]
            for selector in author_selectors:
                try:
                    author_element = row.find_element(By.CSS_SELECTOR, selector)
                    author = author_element.text
                    break
                except NoSuchElementException:
                    continue

            return {
                "title": title,
                "date": date,
                "author": author,
                "url": thread_url
            }

        except Exception as e:
            logger.warning(f"Error extracting metadata from row {row_index}: {e}")
            return None

    def extract_thread_content(self, thread_data: Dict) -> str:
        """
        Visits a thread URL and extracts the conversation content.

        Args:
            thread_data: Dictionary containing thread metadata

        Returns:
            Extracted text content
        """
        logger.debug(f"Fetching content for: {thread_data['title'][:50]}...")

        try:
            self.driver.get(thread_data['url'])
            time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))

            # Wait for main content to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']")))

            # Target specific message containers instead of entire main area
            message_selectors = [
                "div.GbH70b",  # Common message container
                "div[class*='message']",
                "div[data-message-id]",
            ]

            messages = []
            for selector in message_selectors:
                try:
                    message_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if message_elements:
                        messages = [elem.text for elem in message_elements if elem.text.strip()]
                        break
                except NoSuchElementException:
                    continue

            # Fallback to main content if specific selectors fail
            if not messages:
                logger.debug("Using fallback content extraction")
                main_content = self.driver.find_element(By.CSS_SELECTOR, "div[role='main']")
                return main_content.text

            return "\n\n---\n\n".join(messages)

        except TimeoutException:
            logger.error(f"Timeout loading thread: {thread_data['url']}")
            return "Error: Timeout loading content"
        except Exception as e:
            logger.error(f"Error extracting content from {thread_data['url']}: {e}")
            return f"Error: {str(e)}"

    def scrape_group(self, group_url: str) -> List[Dict]:
        """
        Scrapes all threads from a Google Group with pagination support.

        Args:
            group_url: URL of the Google Group

        Returns:
            List of thread dictionaries with metadata and content
        """
        logger.info(f"Starting scrape of group: {group_url}")

        # Check if already completed
        if self.checkpoint.is_group_completed(group_url):
            logger.info(f"Group already completed: {group_url}")
            return []

        self.driver.get(group_url)
        time.sleep(Config.PAGE_LOAD_WAIT)

        all_threads = []
        page_num = 1
        threads_scraped = 0
        last_thread_index = self.checkpoint.get_last_thread_index(group_url)

        while threads_scraped < Config.MAX_THREADS_PER_GROUP:
            logger.info(f"Scraping page {page_num}...")

            # Scroll to load more threads
            self.scroll_to_load_more(max_scrolls=5)

            # Find all thread rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "div[role='listitem']")
            logger.info(f"Found {len(rows)} threads on page {page_num}")

            # Process each row
            for i, row in enumerate(rows):
                global_index = (page_num - 1) * len(rows) + i

                # Skip if already processed (resume from checkpoint)
                if global_index <= last_thread_index:
                    logger.debug(f"Skipping already processed thread {global_index}")
                    continue

                if threads_scraped >= Config.MAX_THREADS_PER_GROUP:
                    break

                # Extract metadata
                metadata = self.extract_thread_metadata(row, global_index)
                if not metadata:
                    continue

                # Check for duplicate URL
                thread_url = metadata.get('url', '')
                if self.checkpoint.is_url_scraped(thread_url):
                    logger.debug(f"Skipping duplicate URL: {thread_url}")
                    self.checkpoint.update_thread_progress(group_url, global_index)
                    continue

                metadata['group_url'] = group_url

                # Extract content
                content = self.extract_thread_content(metadata)
                metadata['content'] = content

                all_threads.append(metadata)
                threads_scraped += 1

                # Mark URL as scraped and update checkpoint
                self.checkpoint.mark_url_scraped(thread_url)
                self.checkpoint.update_thread_progress(group_url, global_index)

                logger.info(f"[{threads_scraped}/{Config.MAX_THREADS_PER_GROUP}] Scraped: {metadata['title'][:50]}")

                # Polite delay
                time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))

            # Try to navigate to next page
            if threads_scraped < Config.MAX_THREADS_PER_GROUP:
                if not self.navigate_to_next_page():
                    logger.info("No more pages available")
                    break
                page_num += 1
            else:
                break

        # Mark group as completed
        self.checkpoint.mark_group_completed(group_url)
        logger.info(f"Completed scraping {threads_scraped} threads from {group_url}")

        return all_threads

    def run(self) -> List[Dict]:
        """
        Main execution method that scrapes all configured groups.

        Returns:
            List of all scraped thread records
        """
        self.setup_driver()
        all_records = []

        try:
            for group in Config.TARGET_GROUPS:
                group = group.strip()
                threads = self.scrape_group(group)
                all_records.extend(threads)

            # Save to CSV
            if all_records:
                self.save_to_csv(all_records)
                total_unique = self.checkpoint.get_scraped_count()
                logger.info(f"SUCCESS: Scraped {len(all_records)} new conversations")
                logger.info(f"Total unique URLs in database: {total_unique}")
            else:
                logger.warning("No new records scraped (may all be duplicates)")

        except Exception as e:
            logger.error(f"CRITICAL ERROR: {e}", exc_info=True)
            raise
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")

        return all_records

    def save_to_csv(self, records: List[Dict]):
        """Saves scraped records to CSV file."""
        output_path = Path(Config.OUTPUT_FILE)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not records:
            logger.warning("No records to save")
            return

        keys = records[0].keys()
        with open(output_path, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(records)

        logger.info(f"Saved {len(records)} records to {Config.OUTPUT_FILE}")


if __name__ == "__main__":
    scraper = GoogleGroupsScraper()
    scraper.run()