# VAPI Testing Guide - Policy CFP 0101682203

## Quick Start

### Windows (双击运行)
- `scripts/test_cfp.bat` - 交互式选择assistant
- `scripts/test_renewal_transfer.bat` - 测试Renewal assistants (重点测试transfer message)
- `scripts/test_all_cancellation.bat` - 测试所有Cancellation assistants

### Command Line
```bash
# 交互式选择
python scripts/run_test_cfp.py

# 直接指定assistant编号
python scripts/run_test_cfp.py 4  # Renewal 1st & 2nd
python scripts/run_test_cfp.py 5  # Renewal 3rd
python scripts/run_test_cfp.py 1  # Cancellation 1st
```

## Available Assistants

1. **Cancellation 1st Reminder** - Test response restrictions
2. **Cancellation 2nd Reminder** - Test response restrictions
3. **Cancellation 3rd Reminder** - Test response restrictions
4. **Renewal 1st & 2nd Reminder** ⭐ - **Test transfer message**
5. **Renewal 3rd Reminder** ⭐ - **Test transfer message**
6. **Non-Renewal 1st & 2nd Reminder** - Test response restrictions
7. **Non-Renewal 3rd Reminder** - Test response restrictions
8. **Direct Bill 1st & 2nd Reminder** - Test response restrictions
9. **Mortgage Bill 1st Reminder** - Test response restrictions
10. **Mortgage Bill 2nd Reminder** - Test response restrictions

## Testing Focus

### 1. Transfer Message (Renewal Assistants)
- ✅ Check if assistant says "Okay transferring you now" or "Please hold while I transfer"
- ✅ Should NOT silently transfer

### 2. Response Restrictions (All Assistants)
- ✅ Test unexpected input (e.g., "I'm sorry?")
- ✅ Should transfer to live rep instead of glitching
- ✅ Only respond to: yes, no, payment amount, date, etc.

## Test Scripts

- `scripts/run_test_cfp.py` - Main test script (simplified, no logging issues)
- `scripts/test_policy_cfp.py` - Full version with command line args
- `scripts/test_vapi_with_policy.py` - Interactive version with all features

## What the Script Does

1. 🔍 Searches for customer with policy `CFP 0101682203`
2. 📞 Makes real VAPI call using selected assistant
3. ⏳ Waits for call to complete
4. 📊 Shows call results (status, duration, cost)
5. 💬 Displays full transcript
6. ✅ Checks for transfer message (Renewal assistants)
7. 📝 Shows analysis summary

## Notes

- ⚠️ **This makes REAL phone calls** - will incur charges
- Customer phone number will be called
- Script automatically finds customer in Cancellation or Renewal sheets
- All results are displayed in console

