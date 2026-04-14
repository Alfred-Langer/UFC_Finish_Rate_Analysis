"""
events.py

Parses UFC bout data from saved Tapology HTML pages using BeautifulSoup.

Notes:
  - Extracts bout information including fighters, weight division, method of victory, etc.
  - Fighter ages are extracted from the expandable comparison table.
  - Returns an Event object and a list of Bout objects per HTML file.
  - Left fighter on Tapology = fighter_one; right fighter = fighter_two.
  - Bout.fighter_one and Bout.fighter_two are resolved to Fighter IDs inside
    parse_event using lookup_fighter (name → Tapology fighter ID → birth year).
  - Fighter lookups use an in-memory FighterIndex built once per run to avoid
    per-bout database queries.
  - Bout.event_id is left unset during parsing. The loader assigns it after
    the Event has been flushed and given a database ID.
"""

import logging
import re
from collections import defaultdict
import datetime
from datetime import date, time as dt_time, datetime
from pathlib import Path
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from unidecode import unidecode
from config import EVENT_HTML_DIR
from models.bout import Bout
from models.event import Event
from models.fighter import Fighter
from db.session import get_db_session

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

# Tapology method text (lowercase prefix) → Bout.method_of_victory
METHOD_MAP = [
    ("ko/tko",                       "KO/TKO"),
    ("technical submission",         "SUB"),
    ("submission",                   "SUB"),
    ("decision",                     "DEC"),
    ("ends in a draw",               "DRAW"),
    ("result overturned",            "DRAW"),
    ("ends in a no contest",         "NC"),
    ("overturned to no contest",     "NC"),
    ("disqualification",             "DQ"),
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


def parse_height_from_cell(text: str | None) -> float | None:
    """'5\\'4\\" (163cm)' → 64.0, 'N/A' or missing → None"""
    if not text:
        return None
    m = re.match(r"\s*(\d+)'(\d+)\"", text.strip())
    if m:
        return float(int(m.group(1)) * 12 + int(m.group(2)))
    return None


def parse_event_date_and_time(text: str) -> tuple[date, dt_time]:
    """'Saturday 05.29.2010 at 11:00 PM ET' → (date(2010, 5, 29), time(23, 0))"""
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if not m:
        raise ValueError(f"Cannot parse date from: {text!r}")
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))

    parsed_time = dt_time(0, 0)
    if " at " in text:
        time_str = text.split(" at ")[-1].strip()
        time_str = re.sub(r"\s*[A-Z]{2,4}$", "", time_str).strip()
        parsed_time = datetime.strptime(time_str, "%I:%M %p").time()

    return (date(year, month, day), parsed_time)


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
        state = parts[-2]
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


# ── Fighter lookup ─────────────────────────────────────────────────────────────

# name → [(birth_year | None, fighter_id, tapology_id | None), ...]
FighterIndex = dict[str, list[tuple[int | None, int, int | None]]]

# Tapology sometimes displays abbreviated names or previous names of fighterson bout pages that differ from
# the full name stored in the fighters table. We map each abbreviation/previous name to the correct name in our db.
NAME_ALIASES: dict[str, str] = {
    "A. Nogueira":          "Antonio Rodrigo Nogueira",
    "A. Al-Selwady":        "Abdul-Kareem Al-Selwady",
    "Ariane Lipski da Silva": "Ariane da Silva",
    "D. Silva de Andrade":  "Douglas Silva de Andrade",
    "E. Zaleski dos Santos": "Elizeu Zaleski dos Santos",
    "H. Brown Morrison":    "Humberto Brown Morrison",
    "M. Waterson-Gomez":    "Michelle Waterson-Gomez",
    "N. Tumendemberel":     "Nyamjargal Tumendemberel",
    "R. Sokoudjou":         "Rameau Thierry Sokoudjou",
    "Silvana Gomez Juarez": "Silvana Gomez",
    "Ulka Sasaki":          "Yuta Sasaki",
}


def build_fighter_index(session: Session) -> FighterIndex:
    """
    Load every Fighter from the DB in one query and build an in-memory index.
    Called once per pipeline run; all subsequent lookups are O(1) dict access.
    NAME_ALIASES are applied so abbreviated Tapology names resolve correctly.
    """
    index: FighterIndex = defaultdict(list)
    for f in session.query(Fighter).all():
        birth_year = f.date_of_birth.year if f.date_of_birth else None
        index[f.name].append((birth_year, f.id, f.tapology_id))

    for alias, full_name in NAME_ALIASES.items():
        if full_name in index:
            index[alias] = index[full_name]
        else:
            logger.warning(f"NAME_ALIASES: full name '{full_name}' not found in index — alias '{alias}' will not resolve")

    return dict(index)


def parse_tapology_fighter_id(href: str | None) -> int | None:
    """'/fightcenter/fighters/117305-alex-pereira' → 117305"""
    if not href:
        return None
    m = re.search(r"/fighters/(\d+)-", href)
    return int(m.group(1)) if m else None


def lookup_fighter(
    index: FighterIndex,
    name: str,
    age_at_fight: int | None,
    event_date: date,
    tapology_id: int | None = None,
) -> int | None:
    """
    Resolve a fighter name to a Fighter.id using the in-memory FighterIndex.

    Resolution priority:
      1. Name (exact match in index)
      2. Tapology fighter ID — when duplicates remain, filters to candidates whose
         stored tapology_id matches; if tapology_id is None, prefers candidates
         whose stored tapology_id is also None
      3. Birth year (derived from age_at_fight) — applied when duplicates remain
         after step 2
    """
    candidates = list(index.get(name, []))

    if len(candidates) > 1:
        if tapology_id is not None:
            filtered = [c for c in candidates if c[2] == tapology_id]
        else:
            filtered = [c for c in candidates if c[2] is None]
        if filtered:
            candidates = filtered

    if len(candidates) > 1 and age_at_fight is not None:
        birth_years = {event_date.year - age_at_fight, event_date.year - age_at_fight - 1}
        filtered = [c for c in candidates if c[0] in birth_years]
        if filtered:
            candidates = filtered

    if len(candidates) == 1:
        return candidates[0][1]
    elif len(candidates) == 0:
        logger.warning(f"No Fighter found for name='{name}', tapology_id={tapology_id}, age_at_fight={age_at_fight}, event_date={event_date}")
        raise ValueError(f"No Fighter found for name='{name}', tapology_id={tapology_id}, age_at_fight={age_at_fight}, event_date={event_date}")
    else:
        logger.warning(f"Multiple Fighters matched name='{name}', tapology_id={tapology_id}, age_at_fight={age_at_fight}, event_date={event_date} — using first match (id={candidates[0][1]})")
        return candidates[0][1]


# ── Main parser ────────────────────────────────────────────────────────────────


def parse_event(html_path: Path, index: FighterIndex) -> Event:
    """
    Load a saved Tapology event HTML and return an Event object with its
    bouts already attached via event.bouts. SQLAlchemy will assign event_id
    automatically when the event is flushed.

    Bout.fighter_one/fighter_two are resolved to Fighter IDs via
    lookup_fighter using name + Tapology fighter ID + birth year.
    """
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    # ── Event-level metadata ──────────────────────────────────────────────
    heading = soup.select_one("h2.text-2xl, h2.text-xl")
    if not heading:
        raise ValueError(f"Could not locate event name heading: {html_path}")
    event_name = heading.get_text(strip=True)

    # Find a span.text-neutral-700 whose text contains a MM.DD.YYYY date
    date_span = None
    for span in soup.select("span.text-neutral-700"):
        if re.search(r"\d{2}\.\d{2}\.\d{4}", span.get_text()):
            date_span = span
            break

    if not date_span:
        raise ValueError(f"Could not locate event date span: {html_path}")
    event_date, event_time = parse_event_date_and_time(date_span.get_text(strip=True))

    # Location ── "City, State, Country" or "City, Country"
    location_li = None
    for li in soup.select("li"):
        if "Location:" in li.get_text():
            location_li = li
            break

    if not location_li:
        raise ValueError(f"Could not locate location li: {html_path}")
    location_span = location_li.select_one("span.text-neutral-700")
    if not location_span:
        raise ValueError(f"Could not locate location span: {html_path}")
    location_text = location_span.get_text(strip=True)
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
    bout_wrappers = soup.select("div[data-bout-wrapper][id^='boutFullsize']")

    # Pre-index all elements with IDs so per-bout lookups are O(1) instead of
    # triggering a full document traversal on every soup.select_one("#...") call
    id_index = {tag["id"]: tag for tag in soup.find_all(id=True)}

    for bout in bout_wrappers:
        bout_id = bout.get("id")
        tapology_id = bout_id.removeprefix("boutFullsize") if bout_id else None

        if bout_id is None:
            logger.warning(f"Could not identify the bout id for event: {event_name}")

        try:
            # Method of victory
            method_span = bout.select_one("span.uppercase")
            if not method_span:
                raise ValueError("Could not locate method of victory span")
            raw_method = method_span.get_text(strip=True)
            method = map_method(raw_method)

            # Center column: rounds scheduled and weight division
            center = bout.select_one("div.rounded.text-tap_darkgold")
            if not center:
                raise ValueError("Could not locate center column div")

            rounds_el = center.select_one("div.text-xs11")
            if not rounds_el:
                raise ValueError("Could not locate rounds scheduled element")
            rounds_text = rounds_el.get_text(strip=True)
            rounds_scheduled = parse_rounds_scheduled(rounds_text)

            weight_span = center.select_one("span.bg-tap_darkgold")
            if not weight_span:
                raise ValueError("Could not locate weight division span")
            weight_division_text = weight_span.get_text(strip=True)
            weight_division = parse_weight_division(weight_division_text)

            # Fighter names
            left_bio = id_index.get(f"{bout_id}_leftBio")
            right_bio = id_index.get(f"{bout_id}_rightBio")

            if not left_bio or not right_bio:
                raise ValueError(f"Could not locate fighter bio divs for bout {bout_id}")

            left_name_el = left_bio.select_one("a.link-primary-red")
            right_name_el = right_bio.select_one("a.link-primary-red")

            if not left_name_el or not right_name_el:
                raise ValueError(f"Could not locate fighter name links for bout {bout_id}")

            left_name = unidecode(left_name_el.get_text(strip=True))
            right_name = unidecode(right_name_el.get_text(strip=True))

            left_tapology_id = parse_tapology_fighter_id(left_name_el.get("href"))
            right_tapology_id = parse_tapology_fighter_id(right_name_el.get("href"))

            # Determine winner
            if left_bio.select_one("div.bg-green-500"):
                winner = "fighter_one"
            elif left_bio.select_one("div.bg-blue-500"):
                winner = "draw"
            else:
                winner = "fighter_two"

            # Fighter ages from the expandable comparison table
            expanded = id_index.get(f"boutExpandedDetails{tapology_id}")
            left_age = None
            right_age = None

            if expanded:
                age_row = None
                height_row = None
                for tr in expanded.select("tr"):
                    text = tr.get_text()
                    if "Age at Fight" in text:
                        age_row = tr
                    if "Height" in text:
                        height_row = tr

                if age_row:
                    hidden_tds = age_row.select("td.hidden")
                    left_age = parse_age(hidden_tds[0].get_text()) if len(hidden_tds) > 0 else None
                    right_age = parse_age(hidden_tds[1].get_text()) if len(hidden_tds) > 1 else None

                if height_row:
                    hidden_tds = height_row.select("td.hidden")

            fighter_one_id = lookup_fighter(index, left_name, left_age, event_date, left_tapology_id)
            fighter_two_id = lookup_fighter(index, right_name, right_age, event_date, right_tapology_id)
                
            event.bouts.append(Bout(
                fighter_one=fighter_one_id,
                fighter_one_age_at_bout=left_age,
                fighter_two=fighter_two_id,
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

    return event


# ── Aggregate parser ───────────────────────────────────────────────────────────


def parse_all_events(session: Session) -> list[Event]:
    """
    Parse all event HTML files in EVENT_HTML_DIR.
    Returns a list of Event objects, each with their bouts attached via event.bouts.
    """
    all_events: list[Event] = []
    failed_files: list[tuple[str, str]] = []

    logger.info("Building fighter index from database...")
    fighter_index = build_fighter_index(session)
    logger.info(f"Fighter index built: {len(fighter_index)} unique names loaded.")

    logger.info(f"Starting to parse files from: {EVENT_HTML_DIR}")
    logger.info("=" * 72)

    for file in EVENT_HTML_DIR.iterdir():
        if file.is_file() and file.suffix == ".html":
            try:
                logger.info(f"Currently parsing: {file.name}")
                event = parse_event(file, fighter_index)

                all_events.append(event)
                logger.info(f"✓ Successfully parsed {len(event.bouts)} bouts from: {file.name}")

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
    total_bouts = sum(len(e.bouts) for e in all_events)
    logger.info(f"Total events parsed: {len(all_events)}")
    logger.info(f"Total bouts parsed: {total_bouts}")

    if failed_files:
        logger.info("Failed files:")
        for filename, error in failed_files:
            logger.error(f"  - {filename}: {error}")

    logger.info("=" * 72)

    return all_events


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with get_db_session() as session:
        events = parse_all_events(session)
        session.commit()
    