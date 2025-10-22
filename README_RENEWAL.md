# Renewal Workflow Documentation

## Overview

The Renewal Workflow is designed to handle Personal Line policy renewal and non-renewal notifications. It uses dynamic sheet discovery to automatically find the current month's renewal sheet and implements a configurable timeline for calling customers.

## Features

- **Dynamic Sheet Discovery**: Automatically finds the current month's renewal sheet
- **Configurable Timeline**: Adjustable calling schedule based on policy expiry dates
- **3-Stage Calling System**: 1st Reminder → 2nd Reminder → Final Reminder
- **Business Day Calculations**: Skips weekends for follow-up dates
- **Multi-Workflow Support**: Can run alongside cancellation workflow

## Configuration

### Environment Variables

Set the workflow type in your environment:

```bash
# For renewal workflow
export WORKFLOW_TYPE=renewals

# For cancellation workflow (default)
export WORKFLOW_TYPE=cancellations
```

### Settings in `config/settings.py`

```python
# Renewal Assistant IDs (to be configured)
RENEWAL_1ST_REMINDER_ASSISTANT_ID = "your_renewal_1st_assistant_id"
RENEWAL_2ND_REMINDER_ASSISTANT_ID = "your_renewal_2nd_assistant_id"
RENEWAL_3RD_REMINDER_ASSISTANT_ID = "your_renewal_3rd_assistant_id"

# Renewal Sheet Configuration
RENEWAL_WORKSPACE_NAME = "ASI"
RENEWAL_SHEET_NAME_PATTERN = "Personal Line - {month_year}"  # e.g., "Personal Line - Nov 2024"

# Renewal Timeline Configuration (based on UW team feedback)
# Contact schedule: 2 weeks before, 1 week before, 1 day before, day of expiry
RENEWAL_CALLING_SCHEDULE = [14, 7, 1, 0]  # Days before expiry to call
RENEWAL_CALLING_START_DAY = 1   # Start calling on 1st of each month
```

## Usage

### Manual Execution

```bash
# Run renewal workflow
python3 main.py

# Or set environment variable
WORKFLOW_TYPE=renewals python3 main.py

# Test mode (no actual calls)
python3 workflows/renewals.py --test
```

### Automated Execution

The system can be configured to run automatically via GitHub Actions or cron jobs.

## Sheet Requirements

### Expected Sheet Structure

The renewal sheet should contain the following columns:

- `company`: Company name
- `phone_number`: Customer phone number
- `policy_expiry_date`: Policy expiration date (YYYY-MM-DD format)
- `renewal_status`: Either "renewal" or "non-renewal"
- `done?`: Checkbox to mark completion
- `renewal_call_stage`: Current call stage (0, 1, 2, 3+)
- `renewal_call_summary`: Call summaries
- `renewal_call_eval`: Call evaluations
- `renewal_f_u_date`: Next follow-up date

### Sheet Naming Convention

Sheets should be named using the pattern: `Personal Line - {Month Year}`

Examples:
- `Personal Line - Nov 2024`
- `Personal Line - Dec 2024`
- `Personal Line - Jan 2025`

## Timeline Logic

### Calling Schedule

1. **Start Date**: Calls begin on the 1st of each month (configurable)
2. **Timeline**: Fixed schedule based on UW team requirements
3. **Stages**: 4-stage calling system with fixed timing

### Stage Progression

- **Stage 0**: 2 weeks before expiry (14 days)
- **Stage 1**: 1 week before expiry (7 days)
- **Stage 2**: 1 day before expiry (1 day)
- **Stage 3**: Day of expiry (0 days)
- **Stage 4+**: No more calls (sequence complete)

## Testing

### Run Tests

```bash
# Test renewal workflow
python3 tests/test_renewal_workflow.py

# Test specific components
python3 -c "from workflows.renewals import get_current_renewal_sheet; print('Testing sheet discovery...')"
```

### Test Mode

Use test mode to simulate calls without making actual phone calls:

```bash
python3 workflows/renewals.py --test
```

## Customization

### Adjust Timeline

To change the calling timeline, update these settings in `config/settings.py`:

```python
# Change the calling schedule (days before expiry)
RENEWAL_CALLING_SCHEDULE = [21, 14, 7, 1, 0]  # Example: 3 weeks, 2 weeks, 1 week, 1 day, day of

# Change to start calling on different day of month
RENEWAL_CALLING_START_DAY = 1
```

### Add New Assistant IDs

Update the assistant IDs in `config/settings.py`:

```python
RENEWAL_1ST_REMINDER_ASSISTANT_ID = "your_actual_assistant_id_here"
RENEWAL_2ND_REMINDER_ASSISTANT_ID = "your_actual_assistant_id_here"
RENEWAL_3RD_REMINDER_ASSISTANT_ID = "your_actual_assistant_id_here"
```

## Troubleshooting

### Common Issues

1. **Sheet Not Found**: Ensure the sheet name follows the pattern and exists in the ASI workspace
2. **No Customers Ready**: Check the timeline settings and customer data
3. **Assistant ID Errors**: Verify the assistant IDs are correct in VAPI

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Existing System

The renewal workflow integrates seamlessly with the existing cancellation workflow:

- **Shared Infrastructure**: Uses the same VAPI and Smartsheet services
- **Unified Main Entry**: Single `main.py` handles both workflows
- **Environment-Based Selection**: Choose workflow via `WORKFLOW_TYPE` environment variable
- **Consistent Logging**: Same logging format and structure

## Future Enhancements

- **Multi-Sheet Support**: Handle multiple renewal sheets simultaneously
- **Advanced Scheduling**: More sophisticated calling schedules
- **Custom Business Rules**: Additional validation and filtering options
- **Reporting**: Enhanced reporting and analytics
