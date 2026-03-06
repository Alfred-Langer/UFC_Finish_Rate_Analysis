import logging
from playwright.sync_api import sync_playwright
from urllib.parse import quote, quote_plus
from scraper.browser import create_browser_context, recover_browser
from scraper.constants import EVENT_NAME_REPLACEMENTS, EXCLUDED_EVENTS
import time
from config import EVENT_NAMES_FILE, EVENT_HTML_DIR, FIGHTER_URLS_FILE, FAILED_EVENT_NAMES_FILE
import random

logger = logging.getLogger(__name__)

DELAY_BETWEEN_SEARCHES = 5

def normalize_ufc_event_names(event_name):
    for find, replace in EVENT_NAME_REPLACEMENTS:
        event_name = event_name.replace(find, replace)
    return event_name


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

            ufc_event_names = [normalize_ufc_event_names(tag.inner_text()) for tag in ufc_event_a_tags]

            EVENT_NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)

            with open(EVENT_NAMES_FILE, "w", encoding="utf-8") as f:
                for event_name in ufc_event_names:
                    if event_name not in EXCLUDED_EVENTS:
                        f.write(event_name + "\n")

            return True
        except Exception as e:
            logger.exception(f"Failed to obtain UFC event names: {type(e).__name__}: {e}")
            raise

        finally:
            browser.close()




def search_event_tapology():

    ufc_events = []
    fighter_urls = []

    with open(EVENT_NAMES_FILE, "r",encoding="utf-8") as f:
        ufc_events = [line.strip() for line in f.readlines()]

    #Create Playright context manager and set it's alias to 'p'
    with sync_playwright() as p:

        #Launch chromium, assign it's reference to 'browser' and open a new page
        browser, page = create_browser_context(p)

        tapology_template_search_string = "https://www.tapology.com/search?term=@@@&search=Submit&mainSearchFilter=events"

        for i, event in enumerate(ufc_events):
            logger.info(f"Processing {i+1}/{len(ufc_events)}: {event}")

            try:
                event_num, event_title = event.split(":", maxsplit=1)
                page.goto(tapology_template_search_string.replace("@@@",quote_plus(event_title)))
            except ValueError:
                logger.warning(f"Event {event} did not include a : in title. Will set event_num to '!@$' and event_title to event")
                event_num = '!@$'
                event_title = event
                page.goto(tapology_template_search_string.replace("@@@",quote_plus(event_title)))

            except Exception as e:
                logger.error(f"Failed to navigate to Tapology for: {event}\n{type(e).__name__}: {e}")
                logger.info("Pausing for 3 minutes before continuing with scrape")
                logger.info("Recreating browser...")
                browser, page = recover_browser(p, browser)
                continue


            event_links = page.locator("td.altA a").all()

            if len(event_links) == 0:
                logger.warning(f"No Tapology event <a> tags were found for: {event}")
                with open(FAILED_EVENT_NAMES_FILE, "a", encoding="utf-8") as fen:
                    fen.write(event + "\n")
                continue

            target_link = event_links[0] if len(event_links) == 1 else next(
                (link for link in event_links if verify_tapology_link(event_num, event_title, link.inner_text())), None
            )

            if target_link:
                save_event_details_to_html(page,target_link,event,fighter_urls)
                time.sleep(DELAY_BETWEEN_SEARCHES + random.randint(-5,5))
            else:
                logger.warning(f"Unable to find a Tapology <a> tag that matched with the event name: {event}")
                with open(FAILED_EVENT_NAMES_FILE, "a", encoding="utf-8") as fen:
                    fen.write(event + "\n")
                continue

        #Ensures there are no duplicate Fighter Profile links within FIGHTER_URLS_FILE
        existing_urls = set()
        if FIGHTER_URLS_FILE.exists():
            with open(FIGHTER_URLS_FILE, "r", encoding="utf-8") as f:
                existing_urls = {line.strip() for line in f if line.strip()}

        with open(FIGHTER_URLS_FILE, "a", encoding="utf-8") as f:
            for url in fighter_urls:
                if url not in existing_urls:
                    f.write(url + "\n")

        return True


def verify_tapology_link(event_num, event_title, link_text):
    if event_num == "!@$" and link_text == event_title:
        return True

    if event_num in link_text or ((not any(char.isdigit() for char in event_num)) and ("UFC" in event_num)):
        return True

    return False

def save_event_details_to_html(page, link, event, fighter_urls):
    try:
        link.click()
        page.wait_for_load_state("domcontentloaded")
        page.evaluate("() => { document.querySelectorAll('script').forEach(el => el.remove()); }")
        content = page.content()

        safe_event_name = event.replace(":", "")
        with open(EVENT_HTML_DIR / f"{safe_event_name}-tapology.html", "w", encoding="utf-8") as f:
            f.write(content)

        # Extract Tapology fighter profile URLs for later use in updating the fighters table
        fighter_links = page.locator("a.link-primary-red").all()

        for link in fighter_links:
            url = link.get_attribute("href")
            if url and "/fighters/" in url and url not in fighter_urls:
                fighter_urls.append(url)

        return True

    except Exception as e:
        logger.error(f"An exception occured while attempting to save the details of the following event: {event}\n{type(e).__name__}-{e}")


if __name__ == "__main__":
    obtain_ufc_event_names()
    time.sleep(10)
    search_event_tapology()
