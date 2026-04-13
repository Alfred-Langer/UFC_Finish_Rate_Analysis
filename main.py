import logging
import sys
from pathlib import Path

#from db.init_db import init_db
#import db.loader as dl
#import parser.events as pe
#import parser.fighters as pf
import scraper.events as se
import scraper.fighters as sf
#from db.session import get_db_session

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    def file_handler(name: str) -> logging.FileHandler:
        h = logging.FileHandler(log_dir / name, encoding="utf-8")
        h.setFormatter(fmt)
        return h

    # Root logger: console + combined file
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    root.addHandler(file_handler("pipeline.log"))

    # Phase-specific files (propagate=True so they still appear in pipeline.log)
    for logger_name, filename in [
        ("scraper", "scraper.log"),
        ("parser",  "parser.log"),
        ("db",      "db.log"),
    ]:
        lg = logging.getLogger(logger_name)
        lg.addHandler(file_handler(filename))


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


# def run_fighters() -> bool:
#     logger.info("=== Phase 2: Fighters ===")
#     try:
#         logger.info("Parsing fighter profiles...")
#         fighters = pf.parse_all_fighters()
#         logger.info(f"Parsed {len(fighters)} fighters.")

#         logger.info("Loading fighters into database...")
#         with get_db_session() as session:
#             dl.load_fighters(session, fighters)
#             session.commit()

#         logger.info("Fighters phase complete.")
#         return True
#     except Exception:
#         logger.exception("Fighters phase failed.")
#         return False


# def run_events() -> bool:
#     logger.info("=== Phase 3: Events & Bouts ===")
#     try:
#         logger.info("Parsing events and bouts (with fighter lookups)...")
#         with get_db_session() as session:
#             events = pe.parse_all_events(session)
#             total_bouts = sum(len(e.bouts) for e in events)
#             logger.info(f"Parsed {len(events)} events and {total_bouts} bouts.")

#             logger.info("Loading events and bouts into database...")
#             dl.load_events(session, events)
#             session.commit()

#         logger.info("Events & bouts phase complete.")
#         return True
#     except Exception:
#         logger.exception("Events & bouts phase failed.")
#         return False


def run_pipeline() -> bool:
    logger.info("Starting UFC data pipeline.")

    if not run_scraping():
        logger.error("Pipeline aborted: scraping phase failed.")
        return False

    #if not run_fighters():
    #    logger.error("Pipeline aborted: fighters phase failed.")
    #    return False

    #if not run_events():
    #    logger.error("Pipeline aborted: events & bouts phase failed.")
    #    return False

    logger.info("Pipeline completed successfully.")
    return True


if __name__ == "__main__":
    setup_logging()
    #init_db()
    success = run_pipeline()
    sys.exit(0 if success else 1)
