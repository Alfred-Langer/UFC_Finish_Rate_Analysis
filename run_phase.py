"""
run_phase.py

CLI tool for running individual pipeline phases during development and testing.

Usage:
    python run_phase.py --phase scrape
    python run_phase.py --phase fighters
    python run_phase.py --phase events
"""

import argparse
import logging
import sys

from main import run_scraping, run_fighters, run_events, setup_logging
from main import run_scraping, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an individual phase of the UFC data pipeline."
    )
    parser.add_argument(
        "--phase",
        choices=("scrape", "fighters", "events"),
        required=True,
        help="Pipeline phase to run: scrape | fighters | events",
    )
    args = parser.parse_args()

    setup_logging()

    if args.phase == "scrape":
        success = run_scraping()
    elif args.phase == "fighters":
       success = run_fighters()
    elif args.phase == "events":
       success = run_events()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
