import logging
import sys
from pathlib import Path

from db.init_db import init_db
import db.loader as dl
import parser.events as pe
import parser.fighters as pf
import scraper.events as se
import scraper.fighters as sf
from db.session import get_db_session

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8"),
        ],
    )


def run_scraping() -> bool:
    logger.info("=== Phase 1: Scraping ===")
    try:
        logger.info("Scraping UFC event names from Wikipedia...")
        se.obtain_ufc_event_names()

        logger.info("Scraping event details from Tapology...")
        se.search_event_tapology()

        logger.info("Scraping fighter profiles from Tapology...")
        sf.search_fighter_tapology()

        logger.info("Scraping phase complete.")
        return True
    except Exception:
        logger.exception("Scraping phase failed.")
        return False


def run_parsing() -> tuple:
    logger.info("=== Phase 2: Parsing ===")

    logger.info("Parsing fighter profiles...")
    fighters = pf.parse_all_fighters()
    logger.info(f"Parsed {len(fighters)} fighters.")

    logger.info("Parsing events and bouts...")
    events, bouts = pe.parse_all_events()
    logger.info(f"Parsed {len(events)} events and {len(bouts)} bouts.")

    return fighters, events, bouts


def run_upload(fighters: list, events: list, bouts: list) -> bool:
    logger.info("=== Phase 3: Upload ===")
    try:
        logger.info("Initializing database schema...")
        init_db()

        logger.info("Loading fighters into database...")
        with get_db_session() as session:
            dl.load_fighters(session, fighters)
            session.commit()

        logger.info("Loading events and bouts into database...")
        with get_db_session() as session:
            dl.load_events(session, events)
            session.commit()

            dl.load_bouts(session, bouts)
            session.commit()

        logger.info("Upload phase complete.")
        return True
    except Exception:
        logger.exception("Upload phase failed.")
        return False


def run_pipeline() -> bool:
    logger.info("Starting UFC data pipeline.")

    if not run_scraping():
        logger.error("Pipeline aborted: scraping phase failed.")
        return False

    try:
        fighters, events, bouts = run_parsing()
    except Exception:
        logger.exception("Pipeline aborted: parsing phase failed.")
        return False

    if not run_upload(fighters, events, bouts):
        logger.error("Pipeline aborted: upload phase failed.")
        return False

    logger.info("Pipeline completed successfully.")
    return True


if __name__ == "__main__":
    setup_logging()
    success = run_pipeline()
    sys.exit(0 if success else 1)
