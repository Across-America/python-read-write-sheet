# AAIS Automated Workflow System

> **Multi-language documentation**: [English](README.md) | [中文](README.zh-CN.md) | [Español](README.es.md)

Automated calling workflows system powered by VAPI and Smartsheet integration. Supports multiple workflow types with intelligent scheduling and timezone handling.

## Features

- **Multi-Workflow Support**: Cancellation reminders, billing notifications, and more
- **3-Stage Calling System**: Automated follow-up sequences with stage-specific AI assistants
- **Intelligent Scheduling**: Business day calculations with automatic daylight saving time handling
- **Batch & Sequential Calling**: Stage 0 uses batch calling, stages 1-2 use sequential calling
- **Smartsheet Integration**: Automatic record updates and call tracking
- **GitHub Actions**: Serverless deployment with automated daily execution

## Project Structure

```
.
├── config/              # Configuration files
├── services/            # External API services
│   ├── smartsheet_service.py
│   └── vapi_service.py
├── workflows/           # Business workflows
│   ├── cancellations.py  # CL1 Project - Cancellation
│   ├── renewals.py       # N1 Project - Renewal
│   ├── non_renewals.py   # N1 Project - Non-Renewal
│   ├── direct_bill.py    # Direct Bill
│   ├── mortgage_bill.py  # Mortgage Bill
│   └── cross_sells.py    # Cross-Sells
├── utils/              # Utility functions
├── tests/              # Formal test files
├── scripts/            # Temporary test/utility scripts
├── docs/               # Documentation files
├── main.py             # Entry point (cron job)
└── .env               # Environment variables
```

See [REPO_STRUCTURE.md](REPO_STRUCTURE.md) for detailed structure explanation.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create `.env` file (only 2 required variables):

```env
SMARTSHEET_ACCESS_TOKEN=your_token
VAPI_API_KEY=your_vapi_key
```

**Other settings in `config/settings.py`**:
- Sheet IDs
- Company phone number ID
- Assistant IDs for each stage
- Test phone number

### 3. Run Tests

```bash
python3 tests/test_vapi_cancellation_flow.py
```

### 4. Manual Run

```bash
python3 main.py
```

## Deployment

### ✅ Recommended: GitHub Actions (Free & Automated)

System is configured with GitHub Actions - **no server required**!

#### 1. Configure GitHub Secrets

In your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these secrets:
   - Name: `SMARTSHEET_ACCESS_TOKEN`, Value: your Smartsheet token
   - Name: `VAPI_API_KEY`, Value: your VAPI API key

#### 2. Enable GitHub Actions

1. Go to **Actions** tab
2. Find "Daily Cancellation Workflow"
3. Click **Enable workflow** (if needed)

#### 3. Verify Execution

- **Automatic**: Runs daily at 4:00 PM Pacific Time (automatic DST handling)
- **Manual**: Actions → Daily Cancellation Workflow → Run workflow
- **View logs**: Actions → Click any run to see detailed logs

#### Daylight Saving Time Handling

The system automatically handles DST transitions:
- Workflow triggers at **both UTC 23:00 and UTC 00:00**
- Python code checks if it's **4:00 PM Pacific time**
- Only executes during the correct hour
- No manual adjustments needed!

**Note**: GitHub Actions scheduled jobs may have 3-15 minute delays. This is normal.

### Alternative: Server Deployment (Not Recommended)

<details>
<summary>Click to expand server deployment instructions (only for special cases)</summary>

#### 1. Upload Code

```bash
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  . user@server:/opt/aais/python-read-write-sheet/
```

#### 2. Install Dependencies

```bash
ssh user@server
cd /opt/aais/python-read-write-sheet
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Setup Cron Job

```bash
crontab -e
```

Add:
```cron
0 16 * * * TZ=America/Los_Angeles cd /opt/aais/python-read-write-sheet && /opt/aais/python-read-write-sheet/venv/bin/python3 main.py >> logs/cron/output.log 2>&1
```

</details>

## Testing

All test files are in the `tests/` directory:

- `test_vapi_cancellation_flow.py` - Complete end-to-end test
- `test_followup_date_calculation.py` - Date calculation test
- `cleanup_test_data.py` - Clean up test data

## Available Workflows

The system supports multiple workflow types, selectable via `WORKFLOW_TYPE` environment variable:

1. **Cancellations** (`cancellations`) - 3-stage cancellation reminders
2. **Renewals** (`renewals`) - Policy renewal notifications (4 stages)
3. **Cross-Sells** (`cross_sells`) - Auto quote offers for monoline home policies
4. **Non-Renewals** (`non_renewals`) - Non-renewal notifications and re-quoting
5. **Direct Bill** (`direct_bill`) - Payment reminders for direct billed policies (3 stages)
6. **Mortgage Bill** (`mortgage_bill`) - Payment reminders for mortgage billed policies (single call)

## Workflow Details

### Cancellations Workflow

#### Daily Execution Flow

1. **4:00 PM Pacific Time** - Automated trigger
2. **Fetch Customers** - Get customers ready for calls today (`f_u_date` = today)
3. **Stage 0 (1st Reminder)** - Batch call initial reminders
4. **Stages 1-2 (2nd-3rd Reminders)** - Sequential follow-up calls
5. **Update Records** - Write call results and next follow-up dates
6. **Manual Verification** - Stage 3 completion requires manual review
7. **Auto Cleanup** - Delete logs older than 30 days

### Customer Filtering Rules

**Skip when**:
- `done?` checkbox is checked
- `company` is empty
- `amount_due` is empty
- `cancellation_date` is empty
- `ai_call_stage >= 3` (call sequence complete)

**Call when**:
- `f_u_date` (follow-up date) = today

### 3-Stage Process

#### **Stage 0 → 1 (1st Reminder)**
- Smartsheet `ai_call_stage` = empty or 0
- Uses `CANCELLATION_1ST_REMINDER_ASSISTANT_ID`
- **Batch calling** (all customers simultaneously)
- Next F/U date = current + (total business days ÷ 3)
- Updates Smartsheet: `ai_call_stage = 1`

#### **Stage 1 → 2 (2nd Reminder)**
- Smartsheet `ai_call_stage = 1`
- Uses `CANCELLATION_2ND_REMINDER_ASSISTANT_ID`
- **Sequential calling** (one by one)
- Next F/U date = current + (remaining business days ÷ 2)
- Updates Smartsheet: `ai_call_stage = 2`

#### **Stage 2 → 3 (3rd Reminder)**
- Smartsheet `ai_call_stage = 2`
- Uses `CANCELLATION_3RD_REMINDER_ASSISTANT_ID`
- **Sequential calling** (one by one)
- No next F/U date
- Updates Smartsheet: `ai_call_stage = 3`
- **Does not auto-mark done** - awaits manual verification

### Business Day Calculation

- Automatically skips weekends (Saturday/Sunday)
- F/U dates guaranteed to fall on business days
- All date calculations exclude weekends

### Updated Fields (Cancellations)

After each call:
- `ai_call_stage`: +1
- `ai_call_summary`: Appends call summary
- `ai_call_eval`: Appends evaluation result
- `f_u_date`: Next follow-up date (empty after Stage 3)
- ~~`done?`~~: Auto-marking disabled, awaits manual review

### Renewals Workflow

**Purpose**: Policy renewal notifications with 4-stage calling schedule

**Calling Schedule**: 14 days before, 7 days before, 1 day before, day of expiry

**Key Features**:
- Dynamic sheet discovery (monthly sheets like "11. November PLR DEV")
- Only calls starting on the 1st of each month
- Uses `Expiration Date` column for timeline calculation
- Filters by `Renewal / Non-Renewal` status

**Required Columns**:
- `Expiration Date` - Policy expiration date
- `Renewal / Non-Renewal` - Renewal status
- `Payee` - Payment method
- `Status` - Policy status
- `Client Phone Number` - Customer phone number

### Cross-Sells Workflow

**Purpose**: Courtesy outreach to monoline home policy customers to offer auto quote

**Key Features**:
- Single call workflow
- Filters for home policy customers only
- Uses `CROSS_SELLS_ASSISTANT_ID`

### Non-Renewals Workflow

**Purpose**: Notify customers about non-renewal and re-quoting process

**Key Features**:
- Single call workflow
- Filters for `Renewal / Non-Renewal = "Non-Renewal"`
- Uses `NON_RENEWALS_ASSISTANT_ID`

### Direct Bill Workflow

**Purpose**: Payment reminders for direct billed policies

**Calling Schedule**: 14 days before, 7 days before, day of (if payment not made)

**Key Features**:
- 3-stage calling system
- Stage 0 (14 days before): Batch calling
- Stage 1 (7 days before): Sequential calling
- Stage 2 (day of): Sequential calling (only if payment not made)
- Automatically skips EFT policies (no follow-ups needed)
- Checks `payment_status` to skip if already paid

**Required Columns**:
- `payment_due_date` or `due_date` - Payment due date
- `payee` - Must contain "Direct Bill"
- `payment_status` - Payment status (checked on day of)

### Mortgage Bill Workflow

**Purpose**: Payment reminders for mortgage billed policies

**Key Features**:
- Single call workflow
- Only calls on day of payment due (or if overdue)
- Only calls if payment not made
- Filters for `payee` containing "Mortgage"
- Uses `MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID`

**Required Columns**:
- `payment_due_date` or `due_date` - Payment due date
- `payee` - Must contain "Mortgage"
- `payment_status` - Payment status (must not be "paid" or "received")

## Logs

Logs are stored in `logs/cron/` directory:
- `cancellations_YYYY-MM-DD.log` - Daily run logs
- `output.log` - Cron output
- Auto-retained for 30 days

## Troubleshooting

View logs:
```bash
tail -f logs/cron/output.log
```

Manual test:
```bash
source venv/bin/activate
python3 main.py
```

## Tech Stack

- Python 3.8+
- Smartsheet API
- VAPI API
- GitHub Actions (scheduled workflows)

## License

See [LICENSE](LICENSE) file for details.
