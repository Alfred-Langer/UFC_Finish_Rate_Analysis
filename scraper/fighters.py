import logging
from bs4 import BeautifulSoup
from curl_cffi import CurlError
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from discord_webhook import DiscordWebhook
from models import fighter
from scraper.browser import create_browser_context, create_session, recover_browser
from config import FIGHTER_HTML_DIR, FIGHTER_URLS_FILE, FAILED_FIGHTER_URLS_FILE, DISCORD_WEBHOOK_URL
import time
import random

logger = logging.getLogger(__name__)

DELAY_BETWEEN_SEARCHES = 4
#Request timeout, memory crash, and connection reset errors are the most common errors we encounter during scraping. 
MINOR_ERROR_CODES = [28, 27, 55] #These are error codes that we consider to be minor and potentially recoverable with retries. 

#403 and 503 errors are typically caused by Tapology temporarily blocking our requests. We consider these to be major errors
#because they require a longer cooldown period and session reset in order to potentially bypass the block.
MAJOR_ERROR_CODE = [503, 403]
session_counter = 0

def send_discord_fail_notifcation(webhook: DiscordWebhook, message: str):
    webhook.content = message
    webhook.execute()

def log_failed_fighter(fighter_url):
        with open(FAILED_FIGHTER_URLS_FILE, "a", encoding="utf-8") as ffu:
            ffu.write(fighter_url + "\n")

def search_fighter_tapology():
    FIGHTER_PROFILE_URL_PREFIX = "https://www.tapology.com"
    DISCORD_WEBHOOK = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    fighter_profile_urls = []
    session_counter = 0
    session_context = None

    with open(FIGHTER_URLS_FILE, "r", encoding="utf-8") as f:
        fighter_profile_urls = [line.strip().split(" | ")[0] for line in f if line.strip()]

    session, session_counter, session_context = create_session(session_counter)
    for i, url in enumerate(fighter_profile_urls):

        #Recreate browser and page objects every 100 iterations to reset memory usage
        if i % 100 == 0 and i > 0:
            session.close()
            session, session_counter, session_context = create_session(session_counter)


        fighter_search_attempts = 0
        while fighter_search_attempts < 3:
            
            request_cooldown = 0
            #Navigate to Fighter Profile
            try:
                logger.info(f"Processing {i+1}/{len(fighter_profile_urls)}: {url}")
                time.sleep(DELAY_BETWEEN_SEARCHES + random.randint(0, 3))

                
                full_url = FIGHTER_PROFILE_URL_PREFIX  + url
                response = session.get(full_url, impersonate=session_context)
                
                if response.status_code != 200:
                    if response.status_code in MINOR_ERROR_CODES:
                        logger.warning(f"Memory Crash or Request Timeout on fighter profile: {full_url}\nStatus Code: {response.status_code}")
                        fighter_search_attempts += 1
                        request_cooldown = 60

                    elif response.status_code in MAJOR_ERROR_CODE:
                        logger.warning(f"Major error for fighter profile: {full_url}\nStatus Code: {response.status_code}")
                        fighter_search_attempts += 1
                        #If we receive a 403/503 error, we pause for 60 minutes before retrying the request in hopes that Tapology will lift the temporary block on our requests.
                        request_cooldown = 3600
                    
                    else:
                        raise Exception(f"Received non-200 status code: {response.status_code} for fighter profile: {full_url}")

                #If we receive a successful response, we break out of the retry loop and continue with parsing the fighter profile details
                else:
                    break

            except Exception as e:

                error_message = f"Request error for fighter profile: {full_url}\n{type(e).__name__}: {e}"
                logger.error(error_message)
                send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING_ERROR(Fighter): {error_message}")
                fighter_search_attempts = 3
                request_cooldown = 300

            #If we encounter any error, we recreate the session and pause for 1 minute before retrying the request.
            #We do this in hopes that if Tapology is blocking our requests temporarily, we can bypass the block by waiting and resetting our session.
            logger.info(f"Pausing for {request_cooldown // 60} minutes before continuing with scrape")
            time.sleep(request_cooldown)
            logger.info("Recreating browser...")
            session.close()
            session, session_counter, session_context = create_session(session_counter)
            continue


        if fighter_search_attempts >= 3:
            error_message = f"Request was not able to successfully navigate to the fighter profile: {full_url} after 3 attempts. Skipping this fighter profile."
            logger.error(error_message)
            send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Fighter): {error_message}")
            log_failed_fighter(full_url)
            continue

        # Parse the HTML from your curl_cffi response
        soup = BeautifulSoup(response.text, 'html.parser')


        #Verify that we successfully navigated to a MMA Fighter Profile
        fighter_profile_header = soup.select("div#fighterPageHeader")

        if len(fighter_profile_header) <= 0:
            error_message = f"Beautiful Soup was not able to locate a MMA Fighter Profile Page Header for fighter url: {url} Skipping this fighter."
            logger.warning(error_message)
            send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Fighter): {error_message}")
            log_failed_fighter(full_url)
            continue

        save_fighter_details_to_html(response, full_url, DISCORD_WEBHOOK)

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
