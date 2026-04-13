import logging
from bs4 import BeautifulSoup
from curl_cffi import CurlError
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from discord_webhook import DiscordWebhook
from scraper.browser import create_browser_context, create_session, recover_browser
from config import FIGHTER_HTML_DIR, FIGHTER_URLS_FILE, FAILED_FIGHTER_URLS_FILE, DISCORD_WEBHOOK_URL
import time
import random

logger = logging.getLogger(__name__)

DELAY_BETWEEN_SEARCHES = 4
REQUEST_TIMEOUT_ERROR_CODE = 28
MEMORY_CRASH_ERROR_CODE = 27
session_counter = 0

def send_discord_fail_notifcation(webhook: DiscordWebhook, message: str):
    webhook.content = message
    webhook.execute()

def log_failed_fighter(fighter_url):
        with open(FAILED_FIGHTER_URLS_FILE, "a", encoding="utf-8") as ffu:
            ffu.write(fighter_url + "\n")

# def search_fighter_tapology():
#     FIGHTER_PROFILE_URL_PREFIX = "https://www.tapology.com"
#     DISCORD_WEBHOOK = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
#     fighter_profile_urls = []

#     with open(FIGHTER_URLS_FILE, "r", encoding="utf-8") as f:
#         fighter_profile_urls = [line.strip().split(" | ")[0] for line in f if line.strip()]

#     #Create Playwright context manager and set it's alias to 'p'
#     with sync_playwright() as p:

#         #Launch chromium, assign it's reference to 'browser' and open a new page
#         browser, page = create_browser_context(p)

#         for i, url in enumerate(fighter_profile_urls):
#             logger.info(f"Processing {i+1}/{len(fighter_profile_urls)}: {url}")
#             time.sleep(DELAY_BETWEEN_SEARCHES + random.randint(0, 3))

#             fighter_search_attempts = 0
#             while fighter_search_attempts < 3:

#                 #Navigate to Fighter Profile
#                 try:
#                     page.goto(FIGHTER_PROFILE_URL_PREFIX + url)
#                     break
#                 except Exception as e:

#                     #Typically the cause for an exception is a short timeout for requests from Tapology or a memory crash from the browser
#                     if isinstance(e, PlaywrightTimeoutError) or "Page crashed" in str(e):
#                         logger.warning(f"Memory Crash or Request Timeout on fighter: {url}\n{type(e).__name__}: {e}")
#                         fighter_search_attempts += 1

#                     #Unknown exception. Will have to inspect logs for further debugging
#                     else:
#                         error_message = f"Unhandled Playwright error for event: {url}\n{type(e).__name__}: {e}"
#                         logger.error(error_message)
#                         send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING_ERROR(Fighter): {error_message}")
#                         fighter_search_attempts = 3

#                     logger.info("Pausing for 1 minute before continuing with scrape")
#                     time.sleep(60)
#                     logger.info("Recreating browser...")
#                     browser, page = recover_browser(p, browser)
#                     continue

#             if fighter_search_attempts >= 3:
#                 error_message = f"Playwright was not able to successfully navigate to the fighter profile: {url} after 3 attempts. Skipping this fighter profile."
#                 logger.error(error_message)
#                 send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Fighter): {error_message}")
#                 log_failed_fighter(url)
#                 continue

#             #Verify that we successfully navigated to a MMA Fighter Profile
#             fighter_profile_header = page.locator("div#fighterPageHeader")

#             if fighter_profile_header.count() <= 0:
#                 error_message = f"Playwright was not able to locate a MMA Fighter Profile Page Header for fighter url: {url} Skipping this fighter."
#                 logger.warning(error_message)
#                 send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Fighter): {error_message}")
#                 log_failed_fighter(url)
#                 continue

#             save_fighter_details_to_html(page, url, DISCORD_WEBHOOK)

#             #Recreate browser and page objects every 100 iterations to reset memory usage
#             if i % 100 == 0 and i > 0:
#                 browser, page = recover_browser(p, browser)

#         return True

def search_fighter_tapology():
    FIGHTER_PROFILE_URL_PREFIX = "https://www.tapology.com"
    DISCORD_WEBHOOK = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    fighter_profile_urls = []
    session_counter = 0

    with open(FIGHTER_URLS_FILE, "r", encoding="utf-8") as f:
        fighter_profile_urls = [line.strip().split(" | ")[0] for line in f if line.strip()]

    session, session_counter= create_session(session_counter)
    for i, url in enumerate(fighter_profile_urls):

        #Recreate browser and page objects every 100 iterations to reset memory usage
        if i % 100 == 0 and i > 0:
            session.close()
            session, session_counter= create_session(session_counter)


        fighter_search_attempts = 0
        while fighter_search_attempts < 3:

            #Navigate to Fighter Profile
            try:
                logger.info(f"Processing {i+1}/{len(fighter_profile_urls)}: {url}")
                time.sleep(DELAY_BETWEEN_SEARCHES + random.randint(0, 3))

                
                url = FIGHTER_PROFILE_URL_PREFIX  + url
                response = session.get(url)
                
                if response.status_code != 200:
                    raise Exception(f"Received non-200 status code: {response.status_code} for fighter profile: {url}")
                
                break

            except CurlError as e:
                #Typically the cause for an exception is a short timeout for requests from Tapology or a memory crash from the browser
                if e.code == REQUEST_TIMEOUT_ERROR_CODE or e.code == MEMORY_CRASH_ERROR_CODE:
                    logger.warning(f"Memory Crash or Request Timeout on fighter profile: {url}\n{type(e).__name__}: {e}")
                    fighter_search_attempts += 1

                #Unknown exception. Will have to inspect logs for further debugging
                else:
                    raise  # re-raise unexpected curl errors

            except Exception as e:

                error_message = f"Unhandled Request error for fighter profile: {url}\n{type(e).__name__}: {e}"
                logger.error(error_message)
                send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING_ERROR(Fighter): {error_message}")
                fighter_search_attempts = 3

            #If we encounter any error, we recreate the session and pause for 1 minute before retrying the request.
            #We do this in hopes that if Tapology is blocking our requests temporarily, we can bypass the block by waiting and resetting our session.
            logger.info("Pausing for 1 minute before continuing with scrape")
            time.sleep(60)
            logger.info("Recreating browser...")
            session.close()
            session, session_counter= create_session(session_counter)
            continue

        if fighter_search_attempts >= 3:
            error_message = f"Playwright was not able to successfully navigate to the fighter profile: {url} after 3 attempts. Skipping this fighter profile."
            logger.error(error_message)
            send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Fighter): {error_message}")
            log_failed_fighter(url)
            continue

        # Parse the HTML from your curl_cffi response
        soup = BeautifulSoup(response.text, 'html.parser')


        #Verify that we successfully navigated to a MMA Fighter Profile
        fighter_profile_header = soup.select("div#fighterPageHeader")

        if fighter_profile_header.count() <= 0:
            error_message = f"Beautiful Soup was not able to locate a MMA Fighter Profile Page Header for fighter url: {url} Skipping this fighter."
            logger.warning(error_message)
            send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Fighter): {error_message}")
            log_failed_fighter(url)
            continue

        save_fighter_details_to_html(response, url, DISCORD_WEBHOOK)

    return True


def save_fighter_details_to_html(response, url, webhook):
    try:
        soup = BeautifulSoup(response.text, "html.parser")
        for script in soup.find_all("script"):
            script.decompose()
        content = str(soup)
        
        fighter_name = url.split("/fighters/", maxsplit=1)[-1]
        FIGHTER_HTML_DIR.mkdir(parents=True, exist_ok=True)
        with open(FIGHTER_HTML_DIR / f"{fighter_name}-tapology-profile.html", "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        error_message = f"An exception occured while attempting to save the details of the following fighter profile: {url}\n{type(e).__name__}-{e}"
        logger.warning(error_message)
        send_discord_fail_notifcation(webhook, f"SCRAPING ERROR(Fighter): {error_message}")



if __name__ == "__main__":
    search_fighter_tapology()
