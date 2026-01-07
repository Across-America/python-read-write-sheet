# CL1 Project - Simple Calling Logic Explanation

## What is CL1?

CL1 is an automated phone calling system that calls customers to remind them about policy cancellations. The system uses AI voice assistants to make these calls automatically.

---

## How It Works - Overview

1. **System runs automatically** twice per day at 11:00 AM and 4:00 PM (Pacific Time)
2. **System finds customers** who need to be called today
3. **System makes calls** using AI voice assistants
4. **System updates records** after each call

---

## Types of Cancellations

The system handles two types of policy cancellations:

### 1. General Cancellation
- **Examples**: Underwriter declined, Unresponsive customer
- **Payment amount**: Not required
- **Timing**: Based on calendar days before expiration

### 2. Non-Payment Cancellation
- **Reason**: Customer didn't pay their bill
- **Payment amount**: Required
- **Timing**: Based on business days before cancellation

---

## Three-Stage Calling System

Each customer receives up to 3 reminder calls:

### Stage 0 - First Reminder
- **When**: 
  - General: 14 days before expiration
  - Non-Payment: When Follow-up Date equals today
- **How**: All customers called at the same time (batch calling)
- **Assistant**: Uses First Reminder Assistant

### Stage 1 - Second Reminder
- **When**: 
  - General: 7 days before expiration
  - Non-Payment: Calculated based on business days
- **How**: One customer at a time (sequential calling)
- **Assistant**: Uses Second Reminder Assistant

### Stage 2 - Final Reminder
- **When**: 
  - General: 3 days before expiration
  - Non-Payment: 1 business day before cancellation
- **How**: One customer at a time (sequential calling)
- **Assistant**: Uses Third Reminder Assistant

---

## Daily Process Flow

### Step 1: System Checks Time
- System only runs at 11:00 AM or 4:00 PM Pacific Time
- System does NOT run on weekends (Saturday or Sunday)
- If it's not the right time or day, system stops

### Step 2: System Finds Customers to Call
The system looks through all customers and finds those who:
- Are NOT marked as "Done"
- Status is NOT "Paid"
- Have the required information (dates, amounts, etc.)
- Were NOT already called today
- Are ready for their next stage call

**For General Cancellation:**
- System checks if today is 14, 7, or 3 days before expiration
- If target date is a weekend, system adjusts to previous Friday
- System can catch up if a call was missed (within 1-3 business days)

**For Non-Payment Cancellation:**
- System checks if Follow-up Date equals today
- If yes, customer is ready to be called

### Step 3: System Groups Customers by Stage
- Stage 0 customers (first reminder)
- Stage 1 customers (second reminder)
- Stage 2 customers (final reminder)

### Step 4: System Makes Calls

**Stage 0 Calls:**
- All customers called at the same time
- Faster process
- Uses First Reminder Assistant

**Stage 1 & 2 Calls:**
- One customer at a time
- More careful process
- Uses Second or Third Reminder Assistant

### Step 5: System Updates Records
After each call, system updates:
- **Call Stage**: Moves to next stage (0 → 1 → 2 → 3)
- **Call Summary**: Records call details including:
  - When call was placed
  - Did client answer?
  - Was full message conveyed?
  - Was voicemail left?
  - Call summary/analysis
- **Next Follow-up Date**: Calculates when next call should be made
- **Call Evaluation**: Records call result

---

## How Next Follow-up Date is Calculated

### General Cancellation
- **After Stage 0 call**: Next call is 7 days before expiration
- **After Stage 1 call**: Next call is 3 days before expiration
- **After Stage 2 call**: No more calls needed

### Non-Payment Cancellation
- **After Stage 0 call**: Next call date is calculated as 1/3 of remaining business days
- **After Stage 1 call**: Next call date is calculated as 1/2 of remaining business days
- **After Stage 2 call**: No more calls needed

**Note**: Business days exclude weekends (Saturday and Sunday)

---

## Customer Filtering Rules

### Customers Are Skipped If:
1. ✅ "Done" checkbox is checked
2. ✅ Status is "Paid"
3. ✅ Already called today
4. ✅ Missing required information:
   - General: Missing expiration date or cancellation date
   - Non-Payment: Missing amount due or cancellation date
5. ✅ All 3 calls already completed (Stage 3 or higher)
6. ✅ Not ready for calling today (wrong date)

### Customers Are Called If:
1. ✅ All required information is present
2. ✅ Not marked as done
3. ✅ Status is not "Paid"
4. ✅ Today is the right date for their stage
5. ✅ Not already called today
6. ✅ Still have calls remaining (Stage < 3)

---

## Manual Calling Script

There is also a manual calling script that can be used to call expired policies.

### How It Works:
1. User specifies a Follow-up Date
2. System finds all customers with that Follow-up Date
3. System filters for expired policies (Cancellation Date ≤ Follow-up Date)
4. System makes batch calls to all expired customers
5. System uses a special Assistant ID for expired policies

### When to Use:
- When you need to call customers for a specific date
- When you need to catch up on missed calls
- For testing purposes

---

## Important Notes

### Weekends
- System does NOT make calls on weekends
- If a call date falls on a weekend, it's moved to the previous Friday
- System can catch up on missed calls within 1-3 business days

### Duplicate Calls
- System checks if customer was already called today
- Prevents duplicate calls on the same day
- Uses call history in the system

### Business Days vs Calendar Days
- **General Cancellation**: Uses calendar days (includes weekends)
- **Non-Payment Cancellation**: Uses business days (excludes weekends)

### Call Results
After each call, system records:
- Whether customer answered
- Whether full message was delivered
- Whether voicemail was left
- Call summary/transcript

---

## Summary

**CL1 is an automated system that:**
1. Runs twice daily (11 AM and 4 PM Pacific Time)
2. Finds customers who need calls today
3. Makes reminder calls in 3 stages
4. Updates records automatically
5. Handles two types of cancellations differently
6. Skips weekends and prevents duplicate calls

**The system is fully automated** - once set up, it runs on its own schedule and handles all the calling and record-keeping automatically.

