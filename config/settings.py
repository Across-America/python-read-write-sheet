"""
Configuration settings for VAPI Batch Calling System
Centralized configuration for API keys, IDs, and constants
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ========================================
# VAPI Configuration
# ========================================
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
# ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"  # Spencer: Call Transfer V2 Campaign
DIRECT_BILL_1ST_REMAINDER_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"  # Direct Bill 1st Reminder
DIRECT_BILL_2ND_REMAINDER_ASSISTANT_ID = "6b4afe6e-9486-48d1-a1b9-87dbdebff1c5"  # Direct Bill 2nd Reminder
MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID = "074860b7-1754-4a51-a48d-a7c53f946913"  # Mortgage Bill 1st Reminder
MORTGAGE_BILL_2ND_REMAINDER_ASSISTANT_ID = "a7cdb965-d0b7-455b-9f43-b01e8b9580e1"  # Mortgage Bill 2nd Reminder
CANCELLATION_1ST_REMINDER_ASSISTANT_ID = "6e5e59f0-1a19-425c-b58e-8ad4f2a80461"  # Cancellation 1st Reminder
CANCELLATION_2ND_REMINDER_ASSISTANT_ID = "8248fab4-433b-4988-9cb3-a965227bdb00"  # Cancellation 2nd Reminder
CANCELLATION_3RD_REMINDER_ASSISTANT_ID = "845b2a4f-084f-43e7-a076-e9f130e512d9"  # Cancellation 3rd Reminder


# 🏢 COMPANY CALLER ID CONFIGURATION
# Requirement: The company number +1 (951) 247-2003 must be displayed
COMPANY_PHONE_NUMBER_ID = "def7dca0-2096-42be-82d7-812eeb7e3ed3"  # +1 (951) 247-2003

# ========================================
# Smartsheet Configuration
# ========================================
SMARTSHEET_ACCESS_TOKEN = os.getenv("SMARTSHEET_ACCESS_TOKEN")
# CANCELLATION_SHEET_ID = 8215129842732932
CANCELLATION_SHEET_ID = 7243781955866500
CANCELLATION_DEV_SHEET_ID = 5146141873098628
CANCELLATION_DEV_2_SHEET_ID = 7243781955866500

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
