# 📁 Scripts 目录

这个目录包含所有临时测试脚本、检查脚本和工具脚本。

## 📋 脚本分类

### 测试脚本 (`test_*.py`)
- `test_renewal_*.py` - Renewal workflow 测试脚本
- `test_non_renewal_now.py` - Non-Renewal workflow 测试
- `test_call_*.py` - VAPI 调用测试
- `test_analysis_extraction.py` - Analysis 提取测试
- `test_last_call_date.py` - Last Call Made Date 测试
- `test_workflows.py` - Workflow 测试

### 检查脚本 (`check_*.py`)
- `check_production_config.py` - 生产环境配置检查
- `check_customer_status.py` - 客户状态检查
- `check_sheet_columns.py` - Sheet 列检查
- `check_specific_customers.py` - 特定客户检查
- `check_upcoming_calls.py` - 即将到来的电话检查
- `check_call_tracking.py` - 电话跟踪检查

### 运行脚本 (`run_*.py`)
- `run_renewal_test_now.py` - 立即运行 Renewal 测试
- `run_renewal_production.py` - 运行 Renewal 生产环境

### 工具脚本
- `show_customers_today.py` - 显示今天的客户
- `list_sheets.py` - 列出所有 sheets
- `deploy_renewal.py` - 部署 Renewal workflow
- `update_env_vapi_key.py` - 更新 .env 中的 VAPI key
- `setup_python_env.py` - Python 环境设置

### PowerShell 脚本 (`*.ps1`)
- `setup_python.ps1` - Python 设置
- `verify_python_setup.ps1` - 验证 Python 设置
- `deep_search_python.ps1` - 深度搜索 Python
- `find_and_run_python.ps1` - 查找并运行 Python
- `run_check_with_python.ps1` - 使用 Python 运行检查

## ⚠️ 注意

这些脚本是开发/测试过程中创建的临时工具，可能不是最新的或已过时。使用前请检查脚本内容。

