"""
events.py

Parses UFC bout data from saved Tapology HTML pages using Playwright.

Notes:
  - Extracts bout information including fighters, weight division, method of victory, etc.
  - Fighter ages are extracted from the expandable comparison table.
  - Returns an Event object and a list of Bout objects per HTML file.
  - Left fighter on Tapology = fighter_one; right fighter = fighter_two.
  - Bout.fighter_one and Bout.fighter_two temporarily store fighter names (str)
    during parsing. The loader resolves these to database IDs before insertion.
  - Bout.event_id is left unset during parsing. The loader assigns it after
    the Event has been flushed and given a database ID.
"""

import logging
import re
from datetime import date
from datetime import time as dt_time
from pathlib import Path
from config import EVENT_HTML_DIR

from playwright.sync_api import sync_playwright
from scraper.browser import create_browser_context

from models.bout import Bout
from models.event import Event

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

# Tapology method text (lowercase prefix) → Bout.method_of_victory
METHOD_MAP = [
    ("ko/tko",               "KO/TKO"),
    ("technical submission", "SUB"),
    ("submission",           "SUB"),
    ("decision",             "DEC"),
    ("ends in a draw",         "DRAW"),
    ("result overturned",     "DRAW"),
    ("ends in a no contest",           "NC"),
    ("overturned to no contest",     "NC"),
    ("disqualification",     "DQ"),
]

WEIGHT_DIVISION_MAP = [
    ("115", "Strawweight"),
    ("125", "Flyweight"),
    ("135", "Bantamweight"),
    ("145", "Featherweight"),
    ("155", "Lightweight"),
    ("170", "Welterweight"),
    ("185", "Middleweight"),
    ("205", "Light Heavyweight"),
    ("265", "Heavyweight"),
]

FINISH_METHODS = {"KO/TKO", "SUB", "DQ"}

# Tapology has some non-standard location formats that don't fit the usual
# "City, State, Country" or "City, Country" patterns. We hardcode exceptions for these:
LOCATION_EXCEPTIONS = {
    "Washington D.C.": ("United States", "Washington D.C."),
    "Singapore": ("Singapore", ""),
    "Abu Dhabi": ("United Arab Emirates", "Abu Dhabi"),
    "Macanazinho Gymnasium": ("Brazil", "Rio de Janeiro"),
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def map_method(raw: str) -> str:
    lower = raw.lower().strip()
    for prefix, value in METHOD_MAP:
        if lower.startswith(prefix):
            return value

    raise ValueError(f"Unrecognised method of victory: {raw!r}")


def parse_age(text: str | None) -> int | None:
    """'30 years, 8 months, 4 days' → 30"""
    if text is None:
        return None
    else:
        m = re.match(r"\s*(\d+)", text.strip())
        return int(m.group(1)) if m else None


def parse_event_date_and_time(text: str) -> tuple[date, str]:
    """'Saturday 05.29.2010 at 11:00 PM ET' → date(2010, 5, 29)"""
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if not m:
        raise ValueError(f"Cannot parse date from: {text!r}")
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    time = text.split(" at ")[-1] if " at " in text else ""
    return (date(year, month, day), time.strip())


def parse_stop_time(text: str) -> dt_time | None:
    """
    Finish:   '2:32 Round 3 of 3, 12:32 Total' → time(0, 2, 32)
    Decision: '3 Rounds, 15:00 Total'           → None
    """
    m = re.match(r"\s*(\d+):(\d+)\s+Round", text.strip())
    if m:
        return dt_time(0, int(m.group(1)), int(m.group(2)))
    return None


def parse_location(text: str) -> tuple[str, str]:
    """
    Parse country and state from a Tapology location string.

    Examples:
      "Las Vegas, Nevada, United States" → ("United States", "Nevada")
      "Abu Dhabi, United Arab Emirates"  → ("United Arab Emirates", "Abu Dhabi")
      "London, England, United Kingdom"  → ("United Kingdom", "England")

    Rule: last segment = country, second-to-last segment = state.
    """
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 2:
        if text in LOCATION_EXCEPTIONS:
            return LOCATION_EXCEPTIONS[text]
        raise ValueError(f"Cannot parse location from: {text!r}")
    else:
        country = parts[-1]
        state   = parts[-2]
        return country, state


def parse_rounds_scheduled(text: str) -> int:
    """'3 x 5' → 3, '5 x 5' → 5, '2 x 5' → 2"""
    m = re.match(r"\s*(\d+)\s*x\s*\d+", text.strip())
    if not m:
        raise ValueError(f"Cannot parse rounds_scheduled from: {text!r}")
    n = int(m.group(1))
    if n not in (2, 3, 5):
        raise ValueError(f"rounds_scheduled must be 2, 3, or 5, got {n}")
    return n

def parse_weight_division(raw: str) -> str:
    if not raw.lower().strip().isnumeric():
        raise ValueError(f"Parsed value is not a valid numeric. Value parsed: {raw}")

    for lb_weight_limit, division in WEIGHT_DIVISION_MAP:
        if lb_weight_limit == raw.lower().strip():
            return division

    return f"Catchweight ({raw})"


# ── Main parser ────────────────────────────────────────────────────────────────

def parse_event(html_path: Path) -> tuple[Event, list[Bout]]:
    """
    Load a saved Tapology event HTML and return a tuple of:
      - A single Event object with event-level metadata
      - A list of Bout objects for each fight on the card

    Note: Bout.event_id and Bout.fighter_one/fighter_two are not resolved
    to database IDs here. The loader handles that after flushing.
    """
    abs_path = Path(html_path).resolve().as_posix()
    file_url = f"file:///{abs_path}"

    with sync_playwright() as p:
        browser, page = create_browser_context(p)
        page.goto(file_url, wait_until="domcontentloaded")

        # ── Event-level metadata ──────────────────────────────────────────────
        event_name = page.locator("h2.text-2xl, h2.text-xl").first.inner_text().strip()

        # Find a span.text-neutral-700 whose text contains a MM.DD.YYYY date
        date_span = (
            page.locator("span.text-neutral-700")
            .filter(has_text=re.compile(r"\d{2}\.\d{2}\.\d{4}"))
            .first
        )
        event_date, event_time = parse_event_date_and_time(date_span.inner_text().strip())

        # Location ── "City, State, Country" or "City, Country"
        location_li   = page.locator("li").filter(has_text="Location:").first
        location_text = location_li.locator("span.text-neutral-700").inner_text().strip()
        country, state = parse_location(location_text)

        # ── Create Event object ───────────────────────────────────────────────
        event = Event(
            title=event_name,
            date=event_date,
            time=event_time,
            country=country,
            state=state,
        )

        # ── Per-bout extraction ───────────────────────────────────────────────
        bout_wrappers = page.locator(
            "div[data-bout-wrapper][id^='boutFullsize']"
        ).all()

        bouts: list[Bout] = []

        for bout in bout_wrappers:
            bout_id     = bout.get_attribute("id")
            tapology_id = bout_id.removeprefix("boutFullsize") if bout_id else None

            if bout_id is None:
                logger.warning(f"Could not identify the bout id for event: {event_name}")

            try:
                # Method of victory
                raw_method = bout.locator("span.uppercase").first.inner_text().strip()
                method     = map_method(raw_method)

                # Center column: rounds scheduled and weight division
                center = bout.locator("div.rounded.text-tap_darkgold").first

                rounds_text      = center.locator("div.text-xs11").first.inner_text().strip()
                rounds_scheduled = parse_rounds_scheduled(rounds_text)

                weight_division_text = center.locator("span.bg-tap_darkgold").inner_text().strip()
                weight_division = parse_weight_division(weight_division_text)

                # Fighter names
                left_bio  = page.locator(f"#{bout_id}_leftBio")
                right_bio = page.locator(f"#{bout_id}_rightBio")
                left_name  = left_bio.locator("a.link-primary-red").first.inner_text().strip()
                right_name = right_bio.locator("a.link-primary-red").first.inner_text().strip()

                # Determine winner
                if left_bio.locator("div.bg-green-500").count() > 0:
                    winner = "fighter_one"
                elif left_bio.locator("div.bg-blue-500").count() > 0:
                    winner = "draw"
                else:
                    winner = "fighter_two"

                # Fighter ages from the expandable comparison table
                expanded   = page.locator(f"#boutExpandedDetails{tapology_id}")
                age_row    = expanded.locator("tr").filter(has_text="Age at Fight").first
                hidden_tds = age_row.locator("td.hidden").all()
                left_age  = parse_age(hidden_tds[0].text_content()) if len(hidden_tds) > 0 else None
                right_age = parse_age(hidden_tds[1].text_content()) if len(hidden_tds) > 1 else None

                bouts.append(Bout(
                    # event_id is assigned by the loader after the Event is flushed
                    fighter_one=left_name,
                    fighter_one_age_at_bout=left_age,
                    fighter_two=right_name,
                    fighter_two_age_at_bout=right_age,
                    weight_division=weight_division,
                    winner=winner,
                    method_of_victory=method,
                    finish=method in FINISH_METHODS,
                    rounds_scheduled=rounds_scheduled,
                ))

            except Exception as exc:
                logger.warning(f"  [WARN] Skipped bout {bout_id} for event {event_name}: {type(exc).__name__}: {exc}")
                continue

        browser.close()
    return event, bouts


# ── Aggregate parser ───────────────────────────────────────────────────────────

def parse_all_events() -> tuple[list[Event], list[Bout]]:
    """
    Parse all event HTML files in EVENT_HTML_DIR.
    Returns a tuple of (all_events, all_bouts).
    """
    all_events: list[Event] = []
    all_bouts: list[Bout] = []
    failed_files: list[tuple[str, str]] = []

    logger.info(f"Starting to parse files from: {EVENT_HTML_DIR}")
    logger.info("=" * 72)

    for file in EVENT_HTML_DIR.iterdir():
        if file.is_file() and file.suffix == ".html":
            try:
                logger.info(f"Currently parsing: {file.name}")
                event, bouts = parse_event(file)

                all_events.append(event)
                all_bouts.extend(bouts)
                logger.info(f"✓ Successfully parsed {len(bouts)} bouts from: {file.name}")

            except Exception as exc:
                failed_files.append((file.name, f"{type(exc).__name__}: {exc}"))
                logger.error(f"✗ Failed to parse {file.name}: {type(exc).__name__}: {exc}")

    # Print summary
    logger.info("=" * 72)
    logger.info("PARSING SUMMARY")
    logger.info("=" * 72)
    logger.info(f"Total files processed: {len(all_events) + len(failed_files)}")
    logger.info(f"Successfully parsed: {len(all_events)} files")
    logger.info(f"Failed: {len(failed_files)} files")
    logger.info(f"Total events parsed: {len(all_events)}")
    logger.info(f"Total bouts parsed: {len(all_bouts)}")

    if failed_files:
        logger.info("Failed files:")
        for filename, error in failed_files:
            logger.error(f"  - {filename}: {error}")

    logger.info("=" * 72)

    return all_events, all_bouts


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    events, bouts = parse_all_events()
