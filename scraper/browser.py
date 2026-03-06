# browser.py

from playwright.sync_api import sync_playwright

HEADLESS_FLAG = True
DEFAULT_TIMEOUT = 60000


def create_browser_context(playwright):
    """Launch browser and return a (browser, page) tuple with standard config."""
    browser = playwright.chromium.launch(headless=HEADLESS_FLAG)
    context = browser.new_context()
    context.set_default_timeout(DEFAULT_TIMEOUT)
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
