"""
Configuration settings for VAPI Batch Calling System
Centralized configuration for API keys, IDs, and constants
"""

import os
from dotenv import load_dotenv

# Load environment variables (handle BOM encoding on Windows)
from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, encoding='utf-8-sig')
else:
    load_dotenv()

# ========================================
# VAPI Configuration
# ========================================
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
# ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"  # Spencer: Call Transfer V2 Campaign
# Shared Assistant IDs for Direct Bill and Non-Renewal workflows
# 14 days before & 7 days before: Shared Assistant (used by Direct Bill Stage 0 & 1)
DIRECT_BILL_1ST_REMAINDER_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"  # Direct Bill 1st Reminder (14 days before)
DIRECT_BILL_2ND_REMAINDER_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"  # Same as 1st (14 days & 7 days before - shared)
DIRECT_BILL_3RD_REMAINDER_ASSISTANT_ID = "your_direct_bill_3rd_assistant_id"  # Direct Bill 3rd Reminder (day of) - shared with Non-Renewal
MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID = "074860b7-1754-4a51-a48d-a7c53f946913"  # Mortgage Bill 1st Reminder
MORTGAGE_BILL_2ND_REMAINDER_ASSISTANT_ID = "a7cdb965-d0b7-455b-9f43-b01e8b9580e1"  # Mortgage Bill 2nd Reminder

# CL1 Project - Cancellation Assistant IDs
CANCELLATION_1ST_REMINDER_ASSISTANT_ID = "6e5e59f0-1a19-425c-b58e-8ad4f2a80461"  # CL1 Project - Cancellation 1st Reminder
CANCELLATION_2ND_REMINDER_ASSISTANT_ID = "8248fab4-433b-4988-9cb3-a965227bdb00"  # CL1 Project - Cancellation 2nd Reminder
CANCELLATION_3RD_REMINDER_ASSISTANT_ID = "845b2a4f-084f-43e7-a076-e9f130e512d9"  # CL1 Project - Cancellation 3rd Reminder


# 🏢 COMPANY CALLER ID CONFIGURATION
# Requirement: The company number +1 (951) 247-2003 must be displayed
COMPANY_PHONE_NUMBER_ID = "def7dca0-2096-42be-82d7-812eeb7e3ed3"  # +1 (951) 247-2003

# ========================================
# Smartsheet Configuration
# ========================================
SMARTSHEET_ACCESS_TOKEN = os.getenv("SMARTSHEET_ACCESS_TOKEN")

# CL1 Project - Cancellation Sheet IDs
CANCELLATION_SHEET_ID = 8215129842732932
CANCELLATION_DEV_SHEET_ID = 5146141873098628
CANCELLATION_DEV_2_SHEET_ID = 7243781955866500

# ========================================
# N1 Project Configuration
# Two workflows based on the renewal sheet: Renewal and Non-Renewal
# Both workflows include payee filtering conditions
# ========================================
# Renewal Assistant IDs
RENEWAL_1ST_REMINDER_ASSISTANT_ID = "a3ff24ea-78d3-4553-a78d-532b0fcdd62f"  # 1st & 2nd Reminder (14 days & 7 days before)
RENEWAL_2ND_REMINDER_ASSISTANT_ID = "a3ff24ea-78d3-4553-a78d-532b0fcdd62f"  # Same as 1st (reuse same Assistant)
RENEWAL_3RD_REMINDER_ASSISTANT_ID = "7a046871-6d1d-470b-b7a4-6856a85391aa"  # 3rd Reminder (1 day before & day of expiry)

# Cross-Sells Assistant ID (for monoline home policy customers - offer auto quote)
CROSS_SELLS_ASSISTANT_ID = "your_cross_sells_assistant_id"  # TODO: Get from VAPI

# Non-Renewals Assistant IDs (notify customers about non-renewal and re-quoting)
NON_RENEWAL_1ST_REMINDER_ASSISTANT_ID = "a56a5740-68ee-4dbc-95a9-8619c5aa2689"  # 1st & 2nd Reminder (14 days & 7 days before)
NON_RENEWAL_2ND_REMINDER_ASSISTANT_ID = "a56a5740-68ee-4dbc-95a9-8619c5aa2689"  # Same as 1st (reuse same Assistant)
NON_RENEWAL_3RD_REMINDER_ASSISTANT_ID = "cc41f0eb-bc92-4b7b-8fc9-1b1ba14c74f9"  # 3rd Reminder (1 day before)
# Legacy: Keep for backward compatibility
NON_RENEWALS_ASSISTANT_ID = NON_RENEWAL_3RD_REMINDER_ASSISTANT_ID

# N1 Project Sheet Configuration (Renewal Sheet)
# All N1 Project workflows use this sheet
RENEWAL_WORKSPACE_NAME = "ASI"
RENEWAL_SHEET_NAME_PATTERN = "Personal Line - {month_year}"  # e.g., "Personal Line - Nov 2024"

# ========================================
# Sheet Configuration
# ========================================
# Current Sheet: "12. December PLR" (production sheet)
# Location: ASI -> Personal Line -> Task Prototype -> Renewal/Non-renewal -> 12. December PLR
# 
# Note: DEV sheet no longer exists. Using production sheet for all operations.
# 
# TO SWITCH TO A DIFFERENT MONTH'S SHEET:
# 1. Update RENEWAL_PLR_SHEET_ID to the new month's sheet ID
# 2. Update RENEWAL_PLR_SHEET_NAME_PATTERN if naming convention changes
# ========================================

RENEWAL_PLR_SHEET_ID = 1719628607737732  # "12. December PLR" - current month sheet
RENEWAL_PLR_SHEET_NAME_PATTERN = "{month_number}. {month_name} PLR"  # e.g., "11. November PLR"

# Renewal Timeline Configuration (based on UW team feedback)
# Contact schedule: 2 weeks before, 1 week before, 1 day before, day of expiry
RENEWAL_CALLING_SCHEDULE = [14, 7, 1, 0]  # Days before expiry to call
RENEWAL_CALLING_START_DAY = 1   # Start calling on 1st of each month

# Direct Bill Timeline Configuration
# Contact schedule: 14 days before, 7 days before, 1 day before (shared with Non-Renewal)
# Based on expiration_date column (same as Renewal and Non-Renewal workflows)
DIRECT_BILL_CALLING_SCHEDULE = [14, 7, 1]  # Days before expiration date to call

# Non-Renewal Timeline Configuration
# Contact schedule: 14 days before, 7 days before, 1 day before (same as Direct Bill)
# Based on expiration_date column
NON_RENEWAL_CALLING_SCHEDULE = [14, 7, 1]  # Days before expiration date to call

# ========================================
# STM1 Project Configuration
# Statement Call Workflow - All American Claims workspace
# ========================================
# STM1 Assistant IDs - TO BE CONFIGURED
STM1_1ST_REMINDER_ASSISTANT_ID = None  # TODO: Configure when assistant IDs are decided
STM1_2ND_REMINDER_ASSISTANT_ID = None  # TODO: Configure when assistant IDs are decided
STM1_3RD_REMINDER_ASSISTANT_ID = None  # TODO: Configure when assistant IDs are decided

# STM1 Sheet Configuration
# Location: All American Claims workspace -> statements call sheet
STM1_SHEET_ID = 3766712882122628  # "statements call" sheet ID
STM1_WORKSPACE_NAME = "All American Claims"
STM1_SHEET_NAME = "statements call"

# STM1 Timeline Configuration - TO BE CONFIGURED
# Contact schedule: To be determined based on STM1 requirements
STM1_CALLING_SCHEDULE = None  # TODO: Configure when workflow schedule is decided (e.g., [14, 7, 1])
STM1_CALLING_START_DAY = None  # TODO: Configure when start day is decided (e.g., 1)

# ========================================
# Call Monitoring Configuration
# ========================================
DEFAULT_CHECK_INTERVAL = 15  # seconds
DEFAULT_MAX_WAIT_TIME = 300  # seconds (5 minutes)
ANALYSIS_WAIT_TIMEOUT = 180  # seconds (3 minutes)

# ========================================
# Testing Configuration
# ========================================
# Test phone number in E.164 format (+[country code][number])
# Used for all test scripts to avoid real customer calls
TEST_CUSTOMER_PHONE = "+13239435582"  # Valid test number for VAPI calls
