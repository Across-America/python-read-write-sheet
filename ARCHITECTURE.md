# 📐 VAPI Batch Call System - Architecture

## 🏗️ **Modular Architecture Overview**

This project has been refactored into a clean, modular architecture that separates concerns and improves maintainability.

```
python-read-write-sheet/
├── config/                      # 📦 Configuration Layer
│   ├── __init__.py
│   └── settings.py             # API keys, IDs, constants
│
├── services/                    # 🔌 Service Layer (External APIs)
│   ├── __init__.py
│   ├── vapi_service.py         # VAPI API client
│   └── smartsheet_service.py   # Smartsheet API client
│
├── utils/                       # 🛠️ Utilities Layer
│   ├── __init__.py
│   └── phone_formatter.py      # Phone number formatting
│
├── workflows/                   # 💼 Business Logic Layer
│   ├── __init__.py
│   └── batch_calling.py        # Batch calling workflows
│
├── main.py                      # 🚀 Main Entry Point
├── requirements.txt
├── README.md
└── LICENSE
```

---

## 📚 **Layer Details**

### 1️⃣ **Configuration Layer** (`config/`)

**Purpose**: Centralized configuration management

**Files**:
- `settings.py`: All API keys, IDs, and constants
  - VAPI API key and Assistant ID
  - Company phone number ID
  - Smartsheet access token and sheet ID
  - Call monitoring parameters

**Benefits**:
- ✅ Single source of truth for configuration
- ✅ Easy to modify settings
- ✅ Prevents hardcoded values scattered across files

---

### 2️⃣ **Services Layer** (`services/`)

**Purpose**: Encapsulate all external API interactions

#### **VAPIService** (`vapi_service.py`)
Handles all VAPI API operations:
- `make_batch_call()` - Initiate batch calls
- `check_call_status()` - Check individual call status
- `wait_for_call_completion()` - Monitor call until completion
- Display call results and analysis

#### **SmartsheetService** (`smartsheet_service.py`)
Handles all Smartsheet API operations:
- `get_not_called_customers()` - Fetch customers needing calls
- `update_call_status()` - Update call status column
- `update_call_result()` - Update call result with VAPI analysis

**Benefits**:
- ✅ Clean API abstraction
- ✅ Easy to mock for testing
- ✅ Reusable across different workflows
- ✅ Single responsibility principle

---

### 3️⃣ **Utilities Layer** (`utils/`)

**Purpose**: Reusable helper functions

**Files**:
- `phone_formatter.py`: Convert phone numbers to E.164 format

**Benefits**:
- ✅ DRY (Don't Repeat Yourself)
- ✅ Easy to unit test
- ✅ Reusable across the project

---

### 4️⃣ **Workflows Layer** (`workflows/`)

**Purpose**: Business logic and orchestration

**Files**:
- `batch_calling.py`: High-level calling workflows
  - `test_single_customer_call()` - Test with one customer
  - `test_batch_call_not_called()` - Batch call all "Not call yet"
  - `show_not_called_customers()` - Display customers without calling

**Benefits**:
- ✅ Separates business logic from API details
- ✅ Easy to add new workflows
- ✅ Clear flow of operations

---

### 5️⃣ **Entry Point** (`main.py`)

**Purpose**: User interface and menu system

**Features**:
- Interactive menu
- Calls appropriate workflow functions
- Clean user experience

---

## 🔄 **Data Flow**

```
User Input (main.py)
    ↓
Workflow (batch_calling.py)
    ↓
Services (vapi_service.py + smartsheet_service.py)
    ↓
External APIs (VAPI + Smartsheet)
    ↓
Services process response
    ↓
Workflow orchestrates updates
    ↓
User sees results
```

---

## 🎯 **Key Benefits of This Architecture**

### **1. Separation of Concerns**
Each module has a single, well-defined responsibility

### **2. Maintainability**
Easy to find and fix bugs - know exactly where to look

### **3. Testability**
Each module can be tested independently

### **4. Scalability**
Easy to add new features without affecting existing code

### **5. Reusability**
Services can be used by different workflows

### **6. Clean Code**
- No code duplication
- Clear naming conventions
- Well-documented functions

---

## 🚀 **Usage**

### **Run the system:**
```bash
python3 main.py
```

### **Import modules in custom scripts:**
```python
from services import VAPIService, SmartsheetService
from workflows import test_single_customer_call

# Use services directly
vapi = VAPIService()
smartsheet = SmartsheetService()

customers = smartsheet.get_not_called_customers()
result = vapi.make_batch_call(customers)
```

---

## 🔧 **Adding New Features**

### **Add a new API:**
1. Create `services/new_api_service.py`
2. Implement service class
3. Export from `services/__init__.py`

### **Add a new workflow:**
1. Add function to `workflows/batch_calling.py` or create new file
2. Export from `workflows/__init__.py`
3. Add menu option in `main.py`

### **Add new utilities:**
1. Create function in `utils/` directory
2. Export from `utils/__init__.py`

---

## 📝 **Migration from Single File**

The original `test_batch_call_not_called.py` (774 lines) has been split into:

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `config/settings.py` | ~40 | Configuration |
| `utils/phone_formatter.py` | ~30 | Phone formatting |
| `services/vapi_service.py` | ~280 | VAPI API |
| `services/smartsheet_service.py` | ~240 | Smartsheet API |
| `workflows/batch_calling.py` | ~140 | Business logic |
| `main.py` | ~50 | Entry point |

**Total**: ~780 lines (slightly more due to documentation and modularity)

**Backup**: Original file saved as `test_batch_call_not_called.py.backup`

---

## ✨ **Best Practices Implemented**

- ✅ **Single Responsibility Principle**: Each module does one thing well
- ✅ **DRY (Don't Repeat Yourself)**: No code duplication
- ✅ **Clear Naming**: Self-documenting code
- ✅ **Documentation**: Docstrings for all functions
- ✅ **Error Handling**: Try-except blocks with clear messages
- ✅ **Configuration Management**: Centralized settings
- ✅ **Modularity**: Easy to extend and maintain
