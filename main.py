#!/usr/bin/env python3
"""
Daily Cancellation Workflow - Main Entry Point
Designed to run as a cron job at PST 4:00 PM daily
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
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

    # Check if it's 4:00 PM Pacific time (handles DST automatically)
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)

    logger.info("=" * 80)
    logger.info("🚀 Daily Cancellation Workflow Started")
    logger.info("=" * 80)
    logger.info(f"📅 Date: {now_pacific.strftime('%Y-%m-%d')}")
    logger.info(f"🕐 Time (Pacific): {now_pacific.strftime('%H:%M:%S %Z')}")
    logger.info(f"🕐 Time (UTC): {datetime.now(ZoneInfo('UTC')).strftime('%H:%M:%S %Z')}")
    logger.info("=" * 80)

    # Only run if it's 4:00 PM hour (16:00) in Pacific time
    # OR 10:35 AM (for testing scheduled runs)
    target_hour = 16  # 4:00 PM
    is_test_time = (now_pacific.hour == 10 and now_pacific.minute >= 35)  # 10:35 AM test

    if now_pacific.hour != target_hour and not is_test_time:
        logger.info(f"⏭️  Skipping: Current Pacific time is {now_pacific.strftime('%I:%M %p')}, not 4:00 PM")
        logger.info(f"   This is expected due to daylight saving time handling")
        logger.info("=" * 80)
        return 0

    if is_test_time:
        logger.info(f"🧪 TEST MODE: Running at {now_pacific.strftime('%I:%M %p')} Pacific")
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
