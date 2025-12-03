import argparse
import logging

from .config import LOG_LEVEL
from .lead_client import LeadTrackerClient
from .task_client import TaskClient
from .sync_logic import SyncService


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-way sync between Lead Tracker and Work Tracker")
    parser.add_argument(
        "--initial",
        action="store_true",
        help="Run initial sync (create tasks for leads); otherwise run incremental sync",
    )
    args = parser.parse_args()

    configure_logging()

    lead_client = LeadTrackerClient()
    task_client = TaskClient()
    service = SyncService(lead_client=lead_client, task_client=task_client)

    service.run_once(initial=args.initial)


if __name__ == "__main__":
    main()


