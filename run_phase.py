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
    """
    Entry point for the UFC data pipeline runner.

    Run a single phase of the pipeline from the terminal:

        python run_phase.py --phase <phase> [--flags BOOL [BOOL ...]]

    Phases:
        scrape      Scrape raw UFC data. Optionally accepts --flags (see below).
        fighters    Process and store fighter data.
        events      Process and store event data.

    Arguments:
        --phase     (required) The pipeline phase to run: scrape | fighters | events
        --flags     (optional, scrape only) A sequence of booleans passed to the
                    scraper as a tuple. Accepted values: true/false, 1/0, yes/no.

    Examples:
        python run_phase.py --phase scrape
        python run_phase.py --phase scrape --flags true false true
        python run_phase.py --phase fighters
        python run_phase.py --phase events

    Exit Codes:
        0   Phase completed successfully.
        1   Phase failed.
    """

    parser = argparse.ArgumentParser(
        description="Run an individual phase of the UFC data pipeline."
    )
    parser.add_argument(
        "--phase",
        choices=("scrape", "fighters", "events"),
        required=True,
        help="Pipeline phase to run: scrape | fighters | events",
    )
    parser.add_argument(
        "--flags",
        nargs="*",
        type=lambda x: x.lower() in ("true", "1", "yes"),
        default=None,
        metavar="BOOL",
        help="Optional tuple of booleans for scrape phase (e.g. --flags true false true)",
    )
    args = parser.parse_args()
    setup_logging()

    if args.phase == "scrape":
        flags = tuple(args.flags) if args.flags is not None else None
        success = run_scraping(flags)
    elif args.phase == "fighters":
        success = run_fighters()
    elif args.phase == "events":
        success = run_events()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()