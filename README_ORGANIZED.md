# VAPI Calling System - Organized Structure

## 📁 Directory Structure

```
python-read-write-sheet/
├── main.py                    # Main entry point
├── core/                      # Core calling functionality
│   ├── __init__.py
│   ├── auto_call_and_update.py    # Main calling workflow
│   ├── batch_call_system.py       # Batch calling system
│   └── make_vapi_call.py          # Direct VAPI calls
├── tools/                     # Data access and utilities
│   ├── __init__.py
│   ├── read_cancellation_dev.py   # Smartsheet data access
│   ├── explore_asi_workspace.py   # ASI workspace tools
│   ├── explore_cancellations.py   # Cancellation data tools
│   ├── find_phone_demo.py         # Phone search demo
│   ├── list_asi_files.py          # ASI file listing
│   ├── list_workspaces.py         # Workspace listing
│   ├── update_call_result.py      # Call result updates
│   └── verify_phone_number.py     # Phone verification
├── tests/                     # Test scripts
│   ├── __init__.py
│   ├── test_auto_call.py          # Main functionality tests
│   └── simple_twilio_test.py      # Twilio integration tests
├── utils/                     # Configuration and utilities
│   ├── __init__.py
│   ├── vapi_fields_config.py      # VAPI field configuration
│   ├── vapi_prompt_templates.py   # Prompt templates
│   └── apply_summary_fix.py       # Summary processing
└── python-read-write-sheet.py     # Original main script
```

## 🚀 Quick Start

### Run the main system:
```bash
python main.py
```

### Make a single call:
```python
from core import auto_call_and_update
auto_call_and_update("24765", "BSNDP-2025-012160-01")
```

### Batch call all customers:
```python
from core import get_all_customers_to_call, batch_call_customers
customers = get_all_customers_to_call()
results = batch_call_customers(customers)
```

## 📋 What Was Cleaned Up

### ✅ Removed Duplicate Files:
- `auto_call_and_update_modified.py` (kept main version)
- `auto_call_and_update_updated.py` (kept main version)
- `quick_call.py` (functionality in make_vapi_call.py)
- `make_call_now.py` (functionality in make_vapi_call.py)
- `quick_phone_test.py` (redundant test)
- `test_vapi_integration.py` (redundant test)
- `quick_test.py` (redundant test)

### ✅ Organized by Function:
- **Core**: Main calling functionality
- **Tools**: Data access and manipulation
- **Tests**: Test scripts
- **Utils**: Configuration and utilities

### ✅ Fixed Import Paths:
- Updated all imports to use relative paths
- Created proper Python packages with `__init__.py`
- Fixed circular import issues

## 🔧 Key Features

1. **Single Call System**: `auto_call_and_update()` - Complete workflow
2. **Batch Call System**: `batch_call_customers()` - Handle hundreds of calls
3. **Direct VAPI Calls**: `make_vapi_call()` - Direct API calls
4. **Load Balancing**: Multiple phone numbers for rate limiting
5. **Interactive Mode**: User-friendly command line interface

## 📞 Usage Examples

### Interactive Mode:
```bash
python main.py
# Choose option 1 for single call
# Choose option 3 for batch calls
```

### Programmatic Usage:
```python
# Single call
from core import auto_call_and_update
success = auto_call_and_update("24765", "BSNDP-2025-012160-01")

# Batch calls
from core import batch_call_customers, get_all_customers_to_call
customers = get_all_customers_to_call()
results = batch_call_customers(customers, delay_between_calls=30)
```

## 🧪 Testing

Run tests:
```bash
python tests/test_auto_call.py
python tests/simple_twilio_test.py
```

## 📝 Configuration

All configuration is in the individual modules. Key settings:
- VAPI API Key and Assistant ID
- Phone number IDs for load balancing
- Smartsheet sheet ID and access token
- Rate limiting settings for batch calls
