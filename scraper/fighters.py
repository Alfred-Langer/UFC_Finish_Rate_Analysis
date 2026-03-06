import logging
from playwright.sync_api import sync_playwright
from scraper.browser import create_browser_context, recover_browser
from config import FIGHTER_HTML_DIR, FIGHTER_URLS_FILE, FAILED_EVENT_NAMES_FILE
import time
import random

logger = logging.getLogger(__name__)

DELAY_BETWEEN_SEARCHES = 5


def search_fighter_tapology():
    FIGHTER_PROFILE_URL_PREFIX = "https://www.tapology.com"
    fighter_profile_urls = []

    with open(FIGHTER_URLS_FILE, "r", encoding="utf-8") as f:
        fighter_profile_urls = [line.strip() for line in f.readlines()]

    #Create Playwright context manager and set it's alias to 'p'
    with sync_playwright() as p:

        #Launch chromium, assign it's reference to 'browser' and open a new page
        browser, page = create_browser_context(p)

        for i, url in enumerate(fighter_profile_urls):
            logger.info(f"Processing {i+1}/{len(fighter_profile_urls)}: {url}")

            #Navigate to Fighter Profile
            try:
                page.goto(FIGHTER_PROFILE_URL_PREFIX + url)

            except Exception as e:
                logger.error(f"Failed to navigate to Tapology for Fighter Profile: {url}\n{type(e).__name__}: {e}")
                logger.info("Recreating browser...")
                browser, page = recover_browser(p, browser)
                continue

            #Verify that we successfully navigated to a MMA Fighter Profile
            fighter_profile_header = page.locator("div#fighterPageHeader")

            if fighter_profile_header.count() <= 0:
                logger.error(f"Error: Unable to verify if Playwright navigated to Fighter Profile Page for URL:{url}")
                with open(FAILED_EVENT_NAMES_FILE, "a", encoding="utf-8") as fen:
                    fen.write(url + "\n")
                continue

            save_fighter_details_to_html(page, url)
            time.sleep(DELAY_BETWEEN_SEARCHES + random.randint(-2, 2))

        return True


def save_fighter_details_to_html(page, url):
    try:
        page.evaluate("() => { document.querySelectorAll('script').forEach(el => el.remove()); }")
        content = page.content()

        fighter_name = url.split("/fighters/", maxsplit=1)[-1]
        FIGHTER_HTML_DIR.mkdir(parents=True, exist_ok=True)
        with open(FIGHTER_HTML_DIR / f"{fighter_name}-tapology-profile.html", "w", encoding="utf-8") as f:
            f.write(content)

        return True

    except Exception as e:
        logger.error(f"An exception occured while attempting to save the details of the following fighter profile: {url}\n{type(e).__name__}-{e}")


if __name__ == "__main__":
    search_fighter_tapology()
