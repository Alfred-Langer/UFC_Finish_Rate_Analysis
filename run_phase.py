"""
run_phase.py

CLI tool for running individual pipeline phases during development and testing.

Usage:
    python run_phase.py --phase scrape
    python run_phase.py --phase parse
    python run_phase.py --phase upload
"""

import argparse
import logging
import sys

from main import run_scraping, run_parsing, run_upload, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an individual phase of the UFC data pipeline."
    )
    parser.add_argument(
        "--phase",
        choices=("scrape", "parse", "upload"),
        required=True,
        help="Pipeline phase to run: scrape | parse | upload",
    )
    args = parser.parse_args()

    setup_logging()

    if args.phase == "scrape":
        success = run_scraping()

    elif args.phase == "parse":
        try:
            fighters, events, bouts = run_parsing()
            logger.info(
                f"Parse complete — fighters: {len(fighters)}, "
                f"events: {len(events)}, bouts: {len(bouts)}"
            )
            success = True
        except Exception:
            logger.exception("Parsing phase failed.")
            success = False

    elif args.phase == "upload":
        try:
            fighters, events, bouts = run_parsing()
        except Exception:
            logger.exception("Upload requires successful parsing. Parsing failed.")
            sys.exit(1)
        success = run_upload(fighters, events, bouts)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
