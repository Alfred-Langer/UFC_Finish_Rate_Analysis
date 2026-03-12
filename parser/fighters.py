"""
fighters.py

Parses UFC Fighter data from saved Tapology Fighter Profile HTML pages using BeautifulSoup.

Notes:
  - Extracts fighter information including age, number of bouts, wins/losses/no-contests
  - Returns Fighter model instances ready for database insertion.
"""

import logging
import re
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from config import FIGHTER_HTML_DIR
from models.fighter import Fighter

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────


def parse_sex(soup) -> str:
    """
    Scans all <a> href attributes on the page for 'championship-mens' or
    'championship-womens' to determine the fighter's sex.

    Returns 'M', 'F', or 'NA' if neither substring is found.
    """
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "championship-womens" in href:
            return "F"
        if "championship-mens" in href:
            return "M"
    return "NA"


def parse_nick_name(text: str | None) -> str:
    """'Nickname:The Eagle' → 'The Eagle'"""
    if not text:
        return ""
    m = re.search(r"Nickname:\s*(.+)", text.strip())
    if not m:
        return ""
    name = m.group(1).strip()
    return name if name and name != "N/A" else ""


def parse_record(text: str | None) -> tuple[int, int, int, int, int]:
    """'Pro MMA Record: 22-3-0, 1 NC (Win-Loss-Draw)' → (22, 3, 0, 1, 26)"""
    if not text:
        return (0, 0, 0, 0, 0)

    m = re.search(r"(\d+)-(\d+)-(\d+)(?:,\s*(\d+)\s*NC)?", text)
    if not m:
        return (0, 0, 0, 0, 0)

    wins, losses, draws = int(m.group(1)), int(m.group(2)), int(m.group(3))
    no_contests = int(m.group(4)) if m.group(4) else 0
    number_of_bouts = wins + losses + draws + no_contests
    return (wins, losses, draws, no_contests, number_of_bouts)


def parse_age_and_dob(text: str | None) -> tuple[int | None, date | None]:
    """
    'Age: 46 | Date of Birth: 1979 Mar 20' → (46, date(1979, 3, 20))
    'Age: N/A | Date of Birth: 1979 Mar 20' → (None, date(1979, 3, 20))
    'Age: 46 | Date of Birth: N/A'          → (46, None)
    'Age: N/A | Date of Birth: N/A'         → (None, None)
    """
    if not text:
        return (None, None)

    age_match = re.search(r"Age:\s*(\d+|N/A)", text)
    dob_match = re.search(r"Date of Birth:\s*(\d{4}\s+\w+\s+\d{1,2}|N/A)", text)

    age = None
    if age_match and age_match.group(1) != "N/A":
        age = int(age_match.group(1))

    dob = None
    if dob_match and dob_match.group(1) != "N/A":
        dob = datetime.strptime(dob_match.group(1).strip(), "%Y %b %d").date()

    return (age, dob)


def parse_last_fight_date(text: str | None) -> date | None:
    """'Last Fight: July 19, 2025 in UFC' → date(2025, 7, 19)"""
    if not text:
        return None
    m = re.search(r"(\w+ \d{1,2},\s*\d{4})", text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1).strip(), "%B %d, %Y").date()
    except ValueError:
        return None


def parse_height_and_reach(text: str | None) -> tuple[float | None, float | None]:
    """
    "Height: 5'11\" (181cm) | Reach: 72.5\" (184cm)" → (71.0, 72.5)
    "Height: N/A | Reach: 72.5\" (184cm)"            → (None, 72.5)
    "Height: 5'11\" (181cm) | Reach: N/A"            → (71.0, None)
    "Height: N/A | Reach: N/A"                        → (None, None)

    Height is returned as total inches (feet * 12 + inches).
    Reach is returned as inches.
    """
    if not text:
        return (None, None)

    height_match = re.search(r"Height:\s*(?:(\d+)'(\d+)\"|N/A)", text)
    reach_match = re.search(r"Reach:\s*(?:(\d+(?:\.\d+)?)\"|N/A)", text)

    height = None
    if height_match and height_match.group(1) is not None:
        height = float(int(height_match.group(1)) * 12 + int(height_match.group(2)))

    reach = None
    if reach_match and reach_match.group(1) is not None:
        reach = float(reach_match.group(1))

    return (height, reach)


# ── Main parser ────────────────────────────────────────────────────────────────


def parse_fighter_profile(html_path: Path) -> tuple[Fighter, int]:
    """Load a saved Tapology profile HTML and return a Fighter object and a warning count."""
    warnings = 0

    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    # Extract Fighter Name
    header = soup.select_one("div#fighterPageHeader")
    if not header:
        raise ValueError(f"Could not locate fighterPageHeader: {html_path}")

    name_div = None
    for div in header.select("div.leading-tight"):
        if not re.match(r"^\d+-\d+-\d+$", div.get_text(strip=True)):
            name_div = div
            break

    if name_div is None:
        raise ValueError(f"Could not locate the name of the MMA Fighter profile: {html_path}")
    name = name_div.get_text(strip=True)

    # ── Standard Fighter Details Metadata ──────────────────────────────
    fighter_details_div = soup.select_one("div#standardDetails")
    if not fighter_details_div:
        raise ValueError(f"Could not locate standardDetails: {html_path}")

    # Extract and Parse Nickname
    nick_name_text = None
    for div in fighter_details_div.select("div.items-center"):
        strong = div.find("strong", string=re.compile(r"^(Given )?Name:$"))
        if strong:
            nick_name_text = div.get_text()
            break

    if nick_name_text is None:
        raise ValueError(f"Could not locate the nickname of the MMA Fighter profile: {html_path}")
    nick_name = parse_nick_name(nick_name_text)

    # Extract and Parse MMA Record
    record_div = None
    for div in fighter_details_div.select("div.items-center"):
        if "MMA Record" in div.get_text():
            record_div = div
            break

    if record_div is None:
        raise ValueError(f"Could not locate the record of the MMA Fighter profile: {html_path}")
    wins, losses, draws, no_contests, number_of_bouts = parse_record(record_div.get_text())

    # Extract and Parse Age, Date of Birth, Height, and Reach
    age_height_dob_reach_div = fighter_details_div.select_one("div#standardDetailsHeightAge")

    age, date_of_birth = (None, None)
    height, reach = (None, None)

    if age_height_dob_reach_div:
        age_div = None
        height_div = None
        for div in age_height_dob_reach_div.select("div.flex"):
            text = div.get_text()
            if "Age" in text and age_div is None:
                age_div = div
            if "Height" in text and height_div is None:
                height_div = div

        if age_div:
            age, date_of_birth = parse_age_and_dob(age_div.get_text())
        else:
            logger.warning(f"Could not locate Age for MMA Fighter profile: {html_path}")
            warnings += 1

        if height_div:
            height, reach = parse_height_and_reach(height_div.get_text())
        else:
            logger.warning(f"Could not locate Height for MMA Fighter profile: {html_path}")
            warnings += 1
    else:
        logger.warning(f"Could not locate Age/Height section for MMA Fighter profile: {html_path}")
        warnings += 1

    # Extract and Parse Last Fight Date
    latest_bout_date = None
    for div in fighter_details_div.select("div.items-center"):
        strong = div.find("strong", string=re.compile(r"Last Fight:"))
        if strong:
            latest_bout_date = parse_last_fight_date(div.get_text())
            break
    else:
        logger.warning(f"Could not locate last fight date for MMA Fighter profile: {html_path}")
        warnings += 1

    # Extract all MMA Bout divs and compute finish rate
    all_bout_divs = soup.select("div[data-sport='mma'][data-division='pro']")
    mma_bout_divs = [
        div for div in all_bout_divs
        if div.get("data-status") not in ("cancelled", "upcoming")
        and div.select_one("span[title='Fighter Record Before Fight']")
    ]

    if len(mma_bout_divs) != number_of_bouts:
        logger.warning(
            f"MMA bout div count ({len(mma_bout_divs)}) does not match record ({number_of_bouts}) for: {name}"
        )
        for mma_bout_div in mma_bout_divs:
            record_span = mma_bout_div.select_one("span[title='Fighter Record Before Fight']")
            if record_span:
                logger.warning(f"  - Found bout with fighters: {record_span.get_text()}")
        warnings += 1

    num_finish_victories = 0
    for mma_bout_div in mma_bout_divs:
        win_div = mma_bout_div.select_one("div[data-status='win']")
        if not win_div:
            continue
        method_div = win_div.select_one("div.-rotate-90")
        if not method_div:
            logger.warning(f"Could not find method of victory for MMA Fighter: {name}")
            warnings += 1
            continue
        if "DEC" not in method_div.get_text():
            num_finish_victories += 1

    total_bouts = wins + losses + draws
    finish_rate = num_finish_victories / total_bouts if total_bouts > 0 else 0.0

    # Determine sex from championship href substrings
    sex = parse_sex(soup)

    return Fighter(
        name=name,
        nick_name=nick_name,
        former_nick_names="",
        sex=sex,
        age=age,
        date_of_birth=date_of_birth,
        number_of_total_bouts=number_of_bouts,
        wins=wins,
        losses=losses,
        draws=draws,
        no_contests=no_contests,
        overall_finish_rate=finish_rate,
        latest_bout_date=latest_bout_date,
    ), warnings


# ── Entry point ────────────────────────────────────────────────────────────────


def parse_all_fighters():
    successful_files = []
    failed_files = []
    fighter_models = []
    total_warnings = 0

    logger.info(f"Starting to parse files from: {FIGHTER_HTML_DIR}")
    logger.info("=" * 72)

    for file in sorted(FIGHTER_HTML_DIR.iterdir()):
        if not (file.is_file() and file.suffix == ".html"):
            continue

        logger.info(f"Currently parsing: {file.name}")
        try:
            fighter, warnings = parse_fighter_profile(file)
            total_warnings += warnings
            fighter_models.append(fighter)
            successful_files.append(file.name)
            logger.info(
                f"✓ Successfully parsed: {fighter.name}"
                + (f" ({warnings} warnings)" if warnings else "")
            )
        except Exception as exc:
            failed_files.append(file.name)
            logger.error(f"✗ Failed to parse {file.name}: {type(exc).__name__}: {exc}")

    logger.info("=" * 72)
    logger.info("PARSING SUMMARY")
    logger.info("=" * 72)
    logger.info(f"Total files processed : {len(successful_files) + len(failed_files)}")
    logger.info(f"Successfully parsed   : {len(successful_files)}")
    logger.info(f"Failed                : {len(failed_files)}")
    logger.info(f"Total warnings        : {total_warnings}")

    if failed_files:
        logger.info("Failed files:")
        for filename in failed_files:
            logger.error(f"  - {filename}")

    logger.info("=" * 72)
    return fighter_models


if __name__ == "__main__":
    parse_all_fighters()