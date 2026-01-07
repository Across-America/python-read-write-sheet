# N1 Project - Simple Calling Logic Explanation

## What is N1?

N1 is an automated phone calling system that calls customers about their policy renewals. The system uses AI voice assistants to make these calls automatically.

---

## How It Works - Overview

1. **System runs automatically** once per day at 4:00 PM (Pacific Time)
2. **System finds customers** who need renewal reminders today
3. **System makes calls** using AI voice assistants
4. **System updates records** after each call

---

## Two Types of Calls

N1 handles two different situations:

### 1. Renewal Calls
**Purpose**: Remind customers to renew their policy

**When calls are made**:
- 14 days before policy expires
- 7 days before policy expires
- 1 day before policy expires
- On the day policy expires

**Total**: Up to 4 calls per customer

### 2. Non-Renewal Calls
**Purpose**: Notify customers that their policy will not be renewed and we are working on re-quoting

**When calls are made**:
- 14 days before policy expires
- 7 days before policy expires
- 1 day before policy expires

**Total**: Up to 3 calls per customer

---

## Daily Process Flow

### Step 1: System Checks Time
- System only runs at 4:00 PM Pacific Time
- System does NOT run on weekends (Saturday or Sunday)
- If it's not the right time or day, system stops

### Step 2: System Finds Customers to Call
The system looks through all customers and finds those who:
- Have a policy that expires soon
- Are NOT already called today
- Are ready for their next reminder call
- Have all required information (name, phone, expiration date)

**For Renewal Calls:**
- System checks if today is 14, 7, 1, or 0 days before expiration
- If target date is a weekend, system calls on previous Friday

**For Non-Renewal Calls:**
- System checks if today is 14, 7, or 1 days before expiration
- If target date is a weekend, system calls on previous Friday

### Step 3: System Groups Customers
- Customers ready for first call (14 days before)
- Customers ready for second call (7 days before)
- Customers ready for third call (1 day before)
- Customers ready for final call (renewal only - on expiration day)

### Step 4: System Makes Calls

**First Call (14 days before):**
- All customers called at the same time (batch calling)
- Faster process

**Other Calls (7 days, 1 day, expiration day):**
- One customer at a time (sequential calling)
- More careful process

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

---

## Renewal Calls - Detailed Schedule

### Stage 0 - First Reminder
- **When**: 14 days before policy expires
- **Message**: First reminder about renewal
- **How**: All customers called together

### Stage 1 - Second Reminder
- **When**: 7 days before policy expires
- **Message**: Second reminder about renewal
- **How**: One customer at a time

### Stage 2 - Third Reminder
- **When**: 1 day before policy expires
- **Message**: Final reminder before expiration
- **How**: One customer at a time

### Stage 3 - Final Reminder
- **When**: On the day policy expires
- **Message**: Last chance reminder
- **How**: One customer at a time

---

## Non-Renewal Calls - Detailed Schedule

### Stage 0 - First Notification
- **When**: 14 days before policy expires
- **Message**: Notify about non-renewal and re-quoting
- **How**: All customers called together

### Stage 1 - Second Notification
- **When**: 7 days before policy expires
- **Message**: Second notification about non-renewal
- **How**: One customer at a time

### Stage 2 - Final Notification
- **When**: 1 day before policy expires
- **Message**: Final notification before expiration
- **How**: One customer at a time

---

## Customer Filtering Rules

### Customers Are Skipped If:
1. ✅ Policy already expired
2. ✅ Already called today
3. ✅ Missing required information (name, phone, expiration date)
4. ✅ Wrong status (for non-renewal calls)
5. ✅ All calls already completed

### Customers Are Called If:
1. ✅ All required information is present
2. ✅ Policy expires soon (within calling window)
3. ✅ Today is the right date for their stage
4. ✅ Not already called today
5. ✅ Still have calls remaining

---

## Important Notes

### Weekends
- System does NOT make calls on weekends
- If a call date falls on a weekend, it's moved to the previous Friday
- Example: If call should be Saturday, system calls on Friday instead

### Duplicate Calls
- System checks if customer was already called today
- Prevents duplicate calls on the same day
- Uses call history in the system

### Calendar Days
- All calculations use calendar days (includes weekends)
- But calls are never made on weekends (moved to Friday)

### Call Results
After each call, system records:
- Whether customer answered
- Whether full message was delivered
- Whether voicemail was left
- Call summary/transcript

---

## Special Cases

### Mortgage Bill Customers (Renewal Sheet)
- Some customers have "Mortgage Billed" as payee
- These customers get special calls:
  - 14 days before expiration
  - 7 days before expiration
- No payment amount required for these calls

### Expired After Customers (Renewal Sheet)
- Customers whose policy expired yesterday or earlier
- Get a special call using a different assistant
- Only called once

---

## Summary

**N1 is an automated system that:**
1. Runs once daily at 4:00 PM Pacific Time
2. Finds customers who need renewal reminders today
3. Makes reminder calls in stages (3-4 calls per customer)
4. Updates records automatically
5. Handles both renewal and non-renewal situations
6. Skips weekends and prevents duplicate calls

**The system is fully automated** - once set up, it runs on its own schedule and handles all the calling and record-keeping automatically.

---

## Key Differences from CL1

| Feature | N1 | CL1 |
|---------|----|-----|
| **Run Time** | 4:00 PM only | 11:00 AM and 4:00 PM |
| **Call Stages** | 3-4 stages | 3 stages |
| **Purpose** | Renewal reminders | Cancellation reminders |
| **Types** | Renewal / Non-Renewal | General / Non-Payment |
| **Date Calculation** | Calendar days | Calendar days (General) / Business days (Non-Payment) |

