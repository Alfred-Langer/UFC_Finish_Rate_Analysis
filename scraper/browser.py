# browser.py

from playwright.sync_api import sync_playwright
import random

HEADLESS_FLAG = True
DEFAULT_TIMEOUT = 60000

#These are various contexts that we will apply to our Playwright browser. Cycling through these should help with bot detection.
contexts = (
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone_id": "America/New_York",
    },
    {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "locale": "en-US",
        "timezone_id": "America/Chicago",
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "viewport": {"width": 1536, "height": 864},
        "locale": "en-GB",
        "timezone_id": "Europe/London",
    },
    {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "viewport": {"width": 1680, "height": 1050},
        "locale": "en-US",
        "timezone_id": "America/Los_Angeles",
    },
    {
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone_id": "America/Denver",
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "viewport": {"width": 1366, "height": 768},
        "locale": "en-CA",
        "timezone_id": "America/Toronto",
    },
)

def create_browser_context(playwright, timeout=DEFAULT_TIMEOUT):
    """Launch browser and return a (browser, page) tuple with standard config."""
    browser = playwright.chromium.launch(headless=HEADLESS_FLAG)
    ctx = random.choice(contexts)
    context = browser.new_context(**ctx)
    context.set_default_timeout(timeout)
    context.set_default_navigation_timeout(DEFAULT_TIMEOUT)
    page = context.new_page()
    return browser, page


def recover_browser(playwright, old_browser):
    """Close a failed browser and spin up a fresh one."""
    try:
        old_browser.close()
    except Exception:
        pass
    return create_browser_context(playwright)
