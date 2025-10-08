#!/usr/bin/env python3
"""
Daily Cancellation Workflow - Main Entry Point
Designed to run as a cron job at PST 4:00 PM daily
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from workflows.cancellations import run_multi_stage_batch_calling


# Setup logging
def setup_logging():
    """Setup logging to both file and console"""
    log_dir = Path(__file__).parent / "logs" / "cron"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"cancellations_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


def cleanup_old_logs(days=30):
    """Delete logs older than specified days"""
    log_dir = Path(__file__).parent / "logs" / "cron"
    if not log_dir.exists():
        return

    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

    for log_file in log_dir.glob("*.log"):
        if log_file.stat().st_mtime < cutoff:
            log_file.unlink()


def main():
    """Main entry point for cron job"""
    logger = setup_logging()

    logger.info("=" * 80)
    logger.info("🚀 Daily Cancellation Workflow Started")
    logger.info("=" * 80)
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
    logger.info(f"🕐 Time: {datetime.now().strftime('%H:%M:%S %Z')}")
    logger.info("=" * 80)

    try:
        # Run the multi-stage batch calling workflow
        success = run_multi_stage_batch_calling(
            test_mode=False,      # Production mode
            schedule_at=None,     # Call immediately
            auto_confirm=True     # Skip confirmation (cron mode)
        )

        if success:
            logger.info("=" * 80)
            logger.info("✅ Daily Cancellation Workflow Completed Successfully")
            logger.info("=" * 80)

            # Cleanup old logs
            cleanup_old_logs(days=30)

            return 0
        else:
            logger.error("=" * 80)
            logger.error("❌ Daily Cancellation Workflow Failed")
            logger.error("=" * 80)
            return 1

    except Exception as e:
        logger.exception("❌ Unexpected error occurred:")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
