#!/usr/bin/env python3
"""
AAIS Automated Workflow System - Main Entry Point
Designed to run as a cron job at PST 11:00 AM daily
Supports multiple workflow types: cancellations, billing notifications, etc.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from workflows.cancellations import run_multi_stage_batch_calling, is_weekend
from workflows.renewals import run_renewal_batch_calling
# from workflows.cross_sells import run_cross_sells_calling  # Temporarily disabled
from workflows.non_renewals import run_non_renewals_calling
from workflows.direct_bill import run_direct_bill_batch_calling
from workflows.mortgage_bill import run_mortgage_bill_calling
from workflows.stm1 import run_stm1_batch_calling


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

    # Check if it's 11:00 AM Pacific time (handles DST automatically)
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)

    logger.info("=" * 80)
    logger.info("🚀 AAIS Automated Workflow System Started")
    logger.info("=" * 80)
    logger.info(f"📅 Date: {now_pacific.strftime('%Y-%m-%d')}")
    logger.info(f"🕐 Time (Pacific): {now_pacific.strftime('%H:%M:%S %Z')}")
    logger.info(f"🕐 Time (UTC): {datetime.now(ZoneInfo('UTC')).strftime('%H:%M:%S %Z')}")
    logger.info("=" * 80)

    # Check if manually triggered via GitHub Actions
    import os
    is_manual_trigger = os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch'

    # Determine which workflow to run based on environment variable
    import os
    workflow_type = os.getenv('WORKFLOW_TYPE', 'cancellations')
    
    if is_manual_trigger:
        logger.info("🖱️  Manual trigger detected (workflow_dispatch) - skipping time check")
    else:
        # Determine target hours based on workflow type
        # CL1 (Cancellations): 11:00 AM and 4:00 PM (twice daily)
        # N1 (Renewals, Non-Renewals): 4:00 PM
        # STM1: 9:00 AM (calling hours: 9:00 AM - 5:00 PM)
        if workflow_type == 'cancellations':
            # Cancellations run twice daily: 11:00 AM and 4:00 PM
            target_hours = [11, 16]  # 11:00 AM and 4:00 PM
            target_time_str = "11:00 AM or 4:00 PM"
        elif workflow_type == 'stm1':
            target_hours = [9]  # 9:00 AM (STM1 calling hours: 9:00 AM - 5:00 PM)
            target_time_str = "9:00 AM"
        elif workflow_type in ['renewals', 'non_renewals']:
            target_hours = [16]  # 4:00 PM
            target_time_str = "4:00 PM"
        else:
            # Default to 11:00 AM for other workflows
            target_hours = [11]
            target_time_str = "11:00 AM"

        if now_pacific.hour not in target_hours:
            logger.info(f"⏭️  Skipping: Current Pacific time is {now_pacific.strftime('%I:%M %p')}, not {target_time_str}")
            logger.info(f"   This is expected due to daylight saving time handling")
            logger.info("=" * 80)
            return 0
        
        # Check if today is weekend (skip weekends, no calls on weekends)
        today_date = now_pacific.date()
        if is_weekend(today_date):
            logger.info(f"⏭️  Skipping: Today is {today_date.strftime('%A')} (weekend) - no calls on weekends")
            logger.info("=" * 80)
            return 0

    try:
        
        if workflow_type == 'cancellations':
            logger.info("🔄 Running CL1 Project - Cancellation Workflow")
            # Run the multi-stage batch calling workflow (CL1 Project)
            success = run_multi_stage_batch_calling(
                test_mode=False,      # Production mode
                schedule_at=None,     # Call immediately
                auto_confirm=True     # Skip confirmation (cron mode)
            )
        elif workflow_type == 'renewals':
            logger.info("🔄 Running N1 Project - Renewal Workflow")
            # Run the renewal batch calling workflow (N1 Project)
            success = run_renewal_batch_calling(
                test_mode=False,      # Production mode
                schedule_at=None,     # Call immediately
                auto_confirm=True     # Skip confirmation (cron mode)
            )
        # elif workflow_type == 'cross_sells':
        #     logger.info("🔄 Running N1 Project - Cross-Sells Workflow")
        #     # Run the cross-sells calling workflow (N1 Project)
        #     # Temporarily disabled
        #     success = run_cross_sells_calling(
        #         test_mode=False,      # Production mode
        #         schedule_at=None,     # Call immediately
        #         auto_confirm=True     # Skip confirmation (cron mode)
        #     )
        elif workflow_type == 'non_renewals':
            logger.info("🔄 Running N1 Project - Non-Renewals Workflow")
            # Run the non-renewals calling workflow (N1 Project)
            success = run_non_renewals_calling(
                test_mode=False,      # Production mode
                schedule_at=None,     # Call immediately
                auto_confirm=True     # Skip confirmation (cron mode)
            )
        elif workflow_type == 'direct_bill':
            logger.info("🔄 Running N1 Project - Direct Bill Workflow")
            # Run the direct bill batch calling workflow (N1 Project)
            success = run_direct_bill_batch_calling(
                test_mode=False,      # Production mode
                schedule_at=None,     # Call immediately
                auto_confirm=True     # Skip confirmation (cron mode)
            )
        elif workflow_type == 'mortgage_bill':
            logger.info("🔄 Running Mortgage Bill Workflow")
            # Run the mortgage bill calling workflow
            success = run_mortgage_bill_calling(
                test_mode=False,      # Production mode
                schedule_at=None,     # Call immediately
                auto_confirm=True     # Skip confirmation (cron mode)
            )
        elif workflow_type == 'stm1':
            logger.info("🔄 Running STM1 Project - Statement Call Workflow")
            # Run the STM1 batch calling workflow (Statement Call)
            success = run_stm1_batch_calling(
                test_mode=False,      # Production mode
                schedule_at=None,     # Call immediately
                auto_confirm=True     # Skip confirmation (cron mode)
            )
        else:
            logger.error(f"❌ Unknown workflow type: {workflow_type}")
            logger.error("   Supported types: 'cancellations', 'renewals', 'non_renewals', 'direct_bill', 'mortgage_bill', 'stm1'")
            return 1

        if success:
            logger.info("=" * 80)
            logger.info("✅ AAIS Automated Workflow Completed Successfully")
            logger.info("=" * 80)

            # Cleanup old logs
            cleanup_old_logs(days=30)

            return 0
        else:
            logger.error("=" * 80)
            logger.error("❌ AAIS Automated Workflow Failed")
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
