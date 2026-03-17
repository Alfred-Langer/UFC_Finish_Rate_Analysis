import logging
from discord_webhook import DiscordWebhook
from unidecode import unidecode
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from urllib.parse import quote, quote_plus
from scraper.browser import create_browser_context, recover_browser
from scraper.constants import EVENT_TOKEN_REPLACEMENTS, EVENT_OVERRIDE_REPLACEMENTS, EXCLUDED_EVENTS
import time
from config import EVENT_NAMES_FILE, EVENT_HTML_DIR, FIGHTER_URLS_FILE, FAILED_EVENT_NAMES_FILE, DISCORD_WEBHOOK_URL
import random

logger = logging.getLogger(__name__)

DELAY_BETWEEN_SEARCHES = 12

def normalize_ufc_event_name(event_name):
    for find, replace in EVENT_OVERRIDE_REPLACEMENTS:
        result = event_name.replace(find, replace)
        if result != event_name:
            return result

    for find, replace in EVENT_TOKEN_REPLACEMENTS:
        event_name = event_name.replace(find, replace)
    return event_name

def log_failed_event(event):
        with open(FAILED_EVENT_NAMES_FILE, "a", encoding="utf-8") as fen:
            fen.write(event + "\n")

def send_discord_fail_notifcation(webhook: DiscordWebhook, message: str):
    webhook.content = message
    webhook.execute()

def obtain_ufc_event_names():

    #Create Playright context manager and set it's alias to 'p'
    with sync_playwright() as p:

        #Launch chromium, assign it's reference to 'browser' and open a new page
        browser, page = create_browser_context(p)

        try:
            #Navigate to List of UFC events on Wikipedia
            page.goto("https://en.wikipedia.org/wiki/List_of_UFC_events")

            #Obtain reference to Past Events table
            past_events_table = page.locator("table#Past_events")

            ufc_event_a_tags = past_events_table.locator("td a", has_text="UFC", has_not_text="Apex").all()
            tuf_event_a_tags = past_events_table.locator("td a", has_text="The Ultimate Fighter").all()

            ufc_event_names = [tag.inner_text() for tag in (ufc_event_a_tags + tuf_event_a_tags)]

            EVENT_NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)

            seen = set()
            with open(EVENT_NAMES_FILE, "w", encoding="utf-8") as f:
                for event_name in ufc_event_names:
                    if event_name not in EXCLUDED_EVENTS and event_name not in seen:
                        seen.add(event_name)
                        f.write(event_name + "\n")

            return True
        except Exception as e:
            logger.exception(f"Failed to obtain UFC event names: {type(e).__name__}: {e}")
            raise

        finally:
            browser.close()




def search_event_tapology():

    TAPOLOGY_TEMPLATE_EVENT_SEARCH_STRING = "https://www.tapology.com/search?term=@@@&search=Submit&mainSearchFilter=events"
    DISCORD_WEBHOOK = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    ufc_events = []
    fighter_urls = {}  # url → event name (first event seen wins)

    with open(EVENT_NAMES_FILE, "r",encoding="utf-8") as f:
        ufc_events = [normalize_ufc_event_name(line.strip()) for line in f.readlines()]

    #Create Playright context manager and set it's alias to 'p'
    with sync_playwright() as p:

        #Launch chromium, assign it's reference to 'browser' and open a new page
        browser, page = create_browser_context(p)

        for i, event in enumerate(ufc_events):
            
            event_search_attempts = 0
            while event_search_attempts < 3:
                try:
                    logger.info(f"Processing {i+1}/{len(ufc_events)}: {event}")
                    time.sleep(DELAY_BETWEEN_SEARCHES + random.randint(0,3))
                    if ":" in event:
                        event_num, event_title = event.split(": ", maxsplit=1)
                    else:
                        event_num, event_title = (None, event)

                    page.goto(TAPOLOGY_TEMPLATE_EVENT_SEARCH_STRING.replace("@@@",quote_plus(event_title)))
                    break

                except Exception as e:

                    #Typically the cause for an exception is a short timeout for requests from Tapology or a memory crash from the browser
                    if isinstance(e, PlaywrightTimeoutError) or "Page crashed" in str(e):
                        logger.warning(f"Memory Crash or Request Timeout on event: {event}\n{type(e).__name__}: {e}")
                        event_search_attempts += 1

                    #Unknown exception. Will have to inspect logs for further debugging
                    else:
                        error_message = f"Unhandled Playwright error for event: {event}\n{type(e).__name__}: {e}"
                        logger.error(error_message)
                        send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING_ERROR(Event): {error_message}")
                        event_search_attempts = 3

                    logger.info("Pausing for 1 minute before continuing with scrape")
                    time.sleep(60)
                    logger.info("Recreating browser...")
                    browser, page = recover_browser(p, browser)
                    continue
            
            if event_search_attempts >= 3:
                error_message = f"Playwright was not able to successfully navigate to the event: {event} after 3 attempts. Skipping this event."
                logger.error(error_message)
                send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Event): {error_message}")
                log_failed_event(event)
                continue
            
            #Locate all <a> elements displayed on the page after searching the UFC event in the search bar
            event_links = page.locator("td.altA a").all()

            if len(event_links) == 0:
                error_message = f"No Tapology event <a> tags were found for: {event}. Skipping this event."
                logger.warning(error_message)
                send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Event): {error_message}")
                log_failed_event(event)
                continue
            
            #If there is a <a> element that matches with the current UFC event or if there is only one <a> element, target_link is set to True
            target_link = event_links[0] if len(event_links) == 1 else next(
                (link for link in event_links if verify_tapology_link(event_num, event_title, link.locator('..').inner_text())), None
            )

            if target_link:
                save_event_details_to_html(page,target_link,event,fighter_urls, DISCORD_WEBHOOK)
            else:
                error_message = f"Unable to find a Tapology <a> tag that matched with the event name: {event}. Skipping this event."
                logger.warning(error_message)
                send_discord_fail_notifcation(DISCORD_WEBHOOK, f"SCRAPING ERROR(Event): {error_message}")
                log_failed_event(event)
                continue

            #Recreate browser and page objects every 100 iterations to reset memory usage
            if i % 100 == 0 and i > 0:
                browser, page = recover_browser(p, browser)
        
        # Ensures there are no duplicate Fighter Profile links within FIGHTER_URLS_FILE.
        # Each line is formatted as "url | event_name". Existing entries are not overwritten.
        existing_urls = set()
        if FIGHTER_URLS_FILE.exists():
            with open(FIGHTER_URLS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing_urls.add(line.split(" | ")[0])

        with open(FIGHTER_URLS_FILE, "a", encoding="utf-8") as f:
            for url, event_name in fighter_urls.items():
                if url not in existing_urls:
                    f.write(f"{url} | {event_name}\n")

        return True


def verify_tapology_link(event_num, event_title, link_text):
    def normalize_title(title):
        return unidecode(title.strip().lower().replace("vs.", "vs"))

    if event_num is None:
        return event_title == link_text

    if " | " not in link_text:
        return False

    link_header, link_sub_header = link_text.split(" | ", maxsplit=1)

    if link_header.split(" ", maxsplit=1)[-1].isdigit():
        return event_num == link_header

    return (
        link_header.startswith("UFC")
        and normalize_title(event_title) == normalize_title(link_sub_header)
    )

def save_event_details_to_html(page, link, event, fighter_urls, webhook):
    try:
        link.click()
        page.wait_for_load_state("domcontentloaded")

        #Javascript thatruns within the Playwright browser
        #It allows us to only extract and save the HTML elements containing info that we need for parsing
        content = page.evaluate("""() => {
            const ids = ['primaryDetailsContainer', 'sectionFightCard'];
            const elements = ids.map(id => document.getElementById(id)).filter(Boolean);
            elements.forEach(el => {
                el.querySelectorAll('script, svg').forEach(tag => tag.remove());
            });

            // Collect h2 elements not already inside the two divs to avoid duplication
            const h2s = Array.from(document.querySelectorAll('h2')).filter(
                h2 => !elements.some(el => el.contains(h2))
            );

            const html = [...h2s, ...elements].map(el => el.outerHTML).join('\\n');
            return `<html><body>\\n${html}\\n</body></html>`;
        }""")

        safe_event_name = event.replace(":", "")
        EVENT_HTML_DIR.mkdir(parents=True, exist_ok=True)
        with open(EVENT_HTML_DIR / f"{safe_event_name}-tapology.html", "w", encoding="utf-8") as f:
            f.write(content)

        # Extract Tapology fighter profile URLs for later use in updating the fighters table
        fighter_links = page.locator("a.link-primary-red").all()

        for link in fighter_links:
            url = link.get_attribute("href")
            if url and "/fighters/" in url and url not in fighter_urls:
                fighter_urls[url] = event

    except Exception as e:
        error_message = f"An exception occured while attempting to save the details of the following event: {event}\n{type(e).__name__}-{e}"
        logger.warning(error_message)
        send_discord_fail_notifcation(webhook, f"SCRAPING ERROR(Event): {error_message}")

if __name__ == "__main__":
    obtain_ufc_event_names()
    time.sleep(10)
    search_event_tapology()
