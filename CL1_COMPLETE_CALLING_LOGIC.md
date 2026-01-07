# CL1 项目完整拨打电话逻辑 / CL1 Project Complete Dial Phone Logic

## 目录 / Table of Contents

1. [系统概述 / System Overview](#系统概述--system-overview)
2. [主入口逻辑 / Main Entry Logic](#主入口逻辑--main-entry-logic)
3. [核心工作流程 / Core Workflow](#核心工作流程--core-workflow)
4. [客户筛选逻辑 / Customer Filtering Logic](#客户筛选逻辑--customer-filtering-logic)
5. [拨打阶段系统 / Calling Stage System](#拨打阶段系统--calling-stage-system)
6. [日期计算逻辑 / Date Calculation Logic](#日期计算逻辑--date-calculation-logic)
7. [拨打执行逻辑 / Call Execution Logic](#拨打执行逻辑--call-execution-logic)
8. [更新逻辑 / Update Logic](#更新逻辑--update-logic)
9. [手动拨打脚本 / Manual Calling Script](#手动拨打脚本--manual-calling-script)

---

## 系统概述 / System Overview

### 中文
CL1 项目是一个自动化的保单取消提醒系统，通过 AI 语音助手自动拨打客户电话，提醒他们关于保单取消的重要信息。系统支持两种类型的取消：
- **General Cancellation（一般取消）**: UW Reason、Underwriter Declined、Unresponsive Insured
- **Non-Payment Cancellation（未付款取消）**: 因未付款导致的取消

系统采用三阶段拨打机制：
- **Stage 0 (第1次提醒)**: 使用 `CANCELLATION_1ST_REMINDER_ASSISTANT_ID`
- **Stage 1 (第2次提醒)**: 使用 `CANCELLATION_2ND_REMINDER_ASSISTANT_ID`
- **Stage 2 (第3次提醒)**: 使用 `CANCELLATION_3RD_REMINDER_ASSISTANT_ID`

### English
The CL1 project is an automated policy cancellation reminder system that uses AI voice assistants to automatically call customers and remind them about important policy cancellation information. The system supports two types of cancellations:
- **General Cancellation**: UW Reason, Underwriter Declined, Unresponsive Insured
- **Non-Payment Cancellation**: Cancellation due to non-payment

The system uses a three-stage calling mechanism:
- **Stage 0 (1st Reminder)**: Uses `CANCELLATION_1ST_REMINDER_ASSISTANT_ID`
- **Stage 1 (2nd Reminder)**: Uses `CANCELLATION_2ND_REMINDER_ASSISTANT_ID`
- **Stage 2 (3rd Reminder)**: Uses `CANCELLATION_3RD_REMINDER_ASSISTANT_ID`

---

## 主入口逻辑 / Main Entry Logic

### 文件位置 / File Location
- `main.py` - 主入口文件

### 中文逻辑说明

1. **时间检查 / Time Check**
   - 系统在太平洋时间 11:00 AM 和 4:00 PM 运行（每天两次）
   - 如果当前时间不是这两个时间点，系统会跳过执行
   - 支持手动触发（GitHub Actions workflow_dispatch）

2. **周末检查 / Weekend Check**
   - 如果今天是周末（周六或周日），系统会跳过执行
   - 使用 `is_weekend()` 函数检查

3. **工作流类型 / Workflow Type**
   - 通过环境变量 `WORKFLOW_TYPE` 确定要运行的工作流
   - CL1 对应 `workflow_type == 'cancellations'`

4. **执行调用 / Execution Call**
   ```python
   run_multi_stage_batch_calling(
       test_mode=False,      # 生产模式
       schedule_at=None,     # 立即拨打
       auto_confirm=True     # 跳过确认（cron 模式）
   )
   ```

### English Logic Description

1. **Time Check**
   - System runs at 11:00 AM and 4:00 PM Pacific Time (twice daily)
   - If current time is not one of these times, system skips execution
   - Supports manual trigger (GitHub Actions workflow_dispatch)

2. **Weekend Check**
   - If today is weekend (Saturday or Sunday), system skips execution
   - Uses `is_weekend()` function to check

3. **Workflow Type**
   - Determines workflow to run via environment variable `WORKFLOW_TYPE`
   - CL1 corresponds to `workflow_type == 'cancellations'`

4. **Execution Call**
   ```python
   run_multi_stage_batch_calling(
       test_mode=False,      # Production mode
       schedule_at=None,     # Call immediately
       auto_confirm=True     # Skip confirmation (cron mode)
   )
   ```

---

## 核心工作流程 / Core Workflow

### 文件位置 / File Location
- `workflows/cancellations.py` - 核心工作流文件

### 主函数：`run_multi_stage_batch_calling()`

#### 中文逻辑流程

1. **初始化服务 / Initialize Services**
   ```python
   smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
   vapi_service = VAPIService()
   ```

2. **获取准备拨打的客户 / Get Customers Ready for Calls**
   ```python
   customers_by_stage = get_customers_ready_for_calls(smartsheet_service)
   ```
   - 返回按阶段分组的客户字典：`{0: [...], 1: [...], 2: [...]}`
   - 每个阶段包含该阶段需要拨打的客户列表

3. **检查是否有客户 / Check if Customers Exist**
   - 如果没有客户需要拨打，直接返回成功

4. **显示摘要并确认 / Display Summary and Confirm**
   - 显示每个阶段的客户数量和使用的 Assistant ID
   - 如果不是测试模式且未设置自动确认，会提示用户确认
   - 显示前5个客户的详细信息

5. **按阶段处理客户 / Process Customers by Stage**
   - **Stage 0**: 批量拨打模式（所有客户同时拨打）
   - **Stage 1 & 2**: 顺序拨打模式（一次拨打一个客户）

6. **更新 Smartsheet / Update Smartsheet**
   - 每次成功拨打后，更新客户的阶段、摘要和下次跟进日期

#### English Logic Flow

1. **Initialize Services**
   ```python
   smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
   vapi_service = VAPIService()
   ```

2. **Get Customers Ready for Calls**
   ```python
   customers_by_stage = get_customers_ready_for_calls(smartsheet_service)
   ```
   - Returns customers grouped by stage: `{0: [...], 1: [...], 2: [...]}`
   - Each stage contains list of customers ready for that stage

3. **Check if Customers Exist**
   - If no customers need calling, return success immediately

4. **Display Summary and Confirm**
   - Shows customer count and Assistant ID for each stage
   - If not test mode and auto_confirm not set, prompts user for confirmation
   - Displays details of first 5 customers

5. **Process Customers by Stage**
   - **Stage 0**: Batch calling mode (all customers simultaneously)
   - **Stage 1 & 2**: Sequential calling mode (one customer at a time)

6. **Update Smartsheet**
   - After each successful call, update customer's stage, summary, and next follow-up date

---

## 客户筛选逻辑 / Customer Filtering Logic

### 函数：`get_customers_ready_for_calls()`

#### 中文逻辑说明

1. **获取所有客户 / Get All Customers**
   ```python
   all_customers = smartsheet_service.get_all_customers_with_stages()
   ```

2. **获取今天日期（太平洋时间）/ Get Today's Date (Pacific Time)**
   ```python
   pacific_tz = ZoneInfo("America/Los_Angeles")
   today = datetime.now(pacific_tz).date()
   ```

3. **遍历每个客户进行筛选 / Filter Each Customer**

   **a. 初始验证 / Initial Validation**
   - 调用 `should_skip_row(customer)` 检查是否应该跳过
   - 跳过条件包括：
     - `done?` 复选框已勾选
     - `Status` 为 "Paid"
     - 缺少必需字段（根据取消类型不同）

   **b. 检查今天是否已拨打 / Check if Already Called Today**
   - 调用 `was_called_today(customer, today)` 检查
   - 通过解析 `ai_call_summary` 字段中的 "Call Placed At" 时间戳判断

   **c. 确定取消类型 / Determine Cancellation Type**
   - 调用 `get_cancellation_type(customer)` 获取类型
   - 返回：`'general'`, `'non_payment'`, 或 `'other'`
   - 如果类型为 `'other'`，跳过该客户

   **d. 获取当前阶段 / Get Current Stage**
   - 调用 `get_call_stage(customer)` 获取当前阶段
   - 从 `ai_call_stage` 字段读取（0, 1, 2, 或空/null）
   - 如果阶段 >= 3，跳过（已完成所有电话）

   **e. 根据类型检查是否准备好 / Check if Ready Based on Type**

   **General Cancellation（一般取消）:**
   - 调用 `is_general_cancellation_ready_for_calling(customer, today)`
   - 使用 `expiration_date`（如果为空则使用 `cancellation_date`）
   - 检查是否在以下日期之一：
     - 14 天前（Stage 0）
     - 7 天前（Stage 1）
     - 3 天前（Stage 2）
   - 如果目标日期是周末，调整到前一个周五
   - 支持补打逻辑（如果错过了目标日期，在接下来的1-3个工作日内补打）

   **Non-Payment Cancellation（未付款取消）:**
   - 检查 `f_u_date`（Follow-up Date）是否等于今天
   - 如果 `f_u_date == today`，则准备好拨打
   - 使用 `is_non_payment_cancellation_ready_for_calling()` 进行详细检查
   - 基于工作日计算：14、7、1 个工作日之前

4. **返回按阶段分组的客户 / Return Customers Grouped by Stage**
   ```python
   return {
       0: [...],  # Stage 0 customers
       1: [...],  # Stage 1 customers
       2: [...]   # Stage 2 customers
   }
   ```

#### English Logic Description

1. **Get All Customers**
   ```python
   all_customers = smartsheet_service.get_all_customers_with_stages()
   ```

2. **Get Today's Date (Pacific Time)**
   ```python
   pacific_tz = ZoneInfo("America/Los_Angeles")
   today = datetime.now(pacific_tz).date()
   ```

3. **Filter Each Customer**

   **a. Initial Validation**
   - Calls `should_skip_row(customer)` to check if should skip
   - Skip conditions include:
     - `done?` checkbox is checked
     - `Status` is "Paid"
     - Missing required fields (varies by cancellation type)

   **b. Check if Already Called Today**
   - Calls `was_called_today(customer, today)` to check
   - Parses "Call Placed At" timestamps in `ai_call_summary` field

   **c. Determine Cancellation Type**
   - Calls `get_cancellation_type(customer)` to get type
   - Returns: `'general'`, `'non_payment'`, or `'other'`
   - If type is `'other'`, skip customer

   **d. Get Current Stage**
   - Calls `get_call_stage(customer)` to get current stage
   - Reads from `ai_call_stage` field (0, 1, 2, or empty/null)
   - If stage >= 3, skip (all calls completed)

   **e. Check if Ready Based on Type**

   **General Cancellation:**
   - Calls `is_general_cancellation_ready_for_calling(customer, today)`
   - Uses `expiration_date` (or `cancellation_date` if empty)
   - Checks if today is one of:
     - 14 days before (Stage 0)
     - 7 days before (Stage 1)
     - 3 days before (Stage 2)
   - If target date is weekend, adjusts to previous Friday
   - Supports catch-up logic (if missed target date, catch up within 1-3 business days)

   **Non-Payment Cancellation:**
   - Checks if `f_u_date` (Follow-up Date) equals today
   - If `f_u_date == today`, ready for calling
   - Uses `is_non_payment_cancellation_ready_for_calling()` for detailed check
   - Based on business days: 14, 7, 1 business days before

4. **Return Customers Grouped by Stage**
   ```python
   return {
       0: [...],  # Stage 0 customers
       1: [...],  # Stage 1 customers
       2: [...]   # Stage 2 customers
   }
   ```

---

## 拨打阶段系统 / Calling Stage System

### 阶段映射 / Stage Mapping

#### 中文
- **Stage 0 (第1次提醒)**: 
  - Assistant ID: `CANCELLATION_1ST_REMINDER_ASSISTANT_ID`
  - 拨打模式：批量拨打（所有客户同时拨打）
  
- **Stage 1 (第2次提醒)**:
  - Assistant ID: `CANCELLATION_2ND_REMINDER_ASSISTANT_ID`
  - 拨打模式：顺序拨打（一次一个客户）
  
- **Stage 2 (第3次提醒)**:
  - Assistant ID: `CANCELLATION_3RD_REMINDER_ASSISTANT_ID`
  - 拨打模式：顺序拨打（一次一个客户）

#### English
- **Stage 0 (1st Reminder)**: 
  - Assistant ID: `CANCELLATION_1ST_REMINDER_ASSISTANT_ID`
  - Calling Mode: Batch calling (all customers simultaneously)
  
- **Stage 1 (2nd Reminder)**:
  - Assistant ID: `CANCELLATION_2ND_REMINDER_ASSISTANT_ID`
  - Calling Mode: Sequential calling (one customer at a time)
  
- **Stage 2 (3rd Reminder)**:
  - Assistant ID: `CANCELLATION_3RD_REMINDER_ASSISTANT_ID`
  - Calling Mode: Sequential calling (one customer at a time)

### 阶段获取函数 / Stage Getter Function

```python
def get_call_stage(customer):
    """获取客户的当前拨打阶段"""
    stage = customer.get('ai_call_stage', '')
    if not stage or stage == '' or stage is None:
        return 0
    try:
        return int(stage)
    except (ValueError, TypeError):
        return 0
```

```python
def get_call_stage(customer):
    """Get current calling stage for customer"""
    stage = customer.get('ai_call_stage', '')
    if not stage or stage == '' or stage is None:
        return 0
    try:
        return int(stage)
    except (ValueError, TypeError):
        return 0
```

### Assistant ID 映射 / Assistant ID Mapping

```python
def get_assistant_id_for_stage(stage):
    """获取指定阶段对应的 Assistant ID"""
    assistant_map = {
        0: CANCELLATION_1ST_REMINDER_ASSISTANT_ID,
        1: CANCELLATION_2ND_REMINDER_ASSISTANT_ID,
        2: CANCELLATION_3RD_REMINDER_ASSISTANT_ID
    }
    return assistant_map.get(stage)
```

```python
def get_assistant_id_for_stage(stage):
    """Get appropriate assistant ID for given call stage"""
    assistant_map = {
        0: CANCELLATION_1ST_REMINDER_ASSISTANT_ID,
        1: CANCELLATION_2ND_REMINDER_ASSISTANT_ID,
        2: CANCELLATION_3RD_REMINDER_ASSISTANT_ID
    }
    return assistant_map.get(stage)
```

---

## 日期计算逻辑 / Date Calculation Logic

### 工作日计算函数 / Business Day Calculation Functions

#### 中文

1. **`is_weekend(date)`** - 检查是否为周末
   - 如果 `date.weekday() >= 5`（周六或周日），返回 `True`

2. **`count_business_days(start_date, end_date)`** - 计算工作日数量
   - 计算两个日期之间的工作日数量（排除周末）
   - 包含开始日期和结束日期

3. **`add_business_days(start_date, number_of_business_days)`** - 添加工作日
   - 在开始日期基础上添加指定数量的工作日
   - 自动跳过周末
   - 返回的日期保证是工作日

#### English

1. **`is_weekend(date)`** - Check if date is weekend
   - Returns `True` if `date.weekday() >= 5` (Saturday or Sunday)

2. **`count_business_days(start_date, end_date)`** - Count business days
   - Counts business days between two dates (excluding weekends)
   - Includes both start and end dates

3. **`add_business_days(start_date, number_of_business_days)`** - Add business days
   - Adds specified number of business days to start date
   - Automatically skips weekends
   - Returned date is guaranteed to be a business day

### 下次跟进日期计算 / Next Follow-up Date Calculation

#### 函数：`calculate_next_followup_date(customer, current_stage)`

#### 中文逻辑

**General Cancellation（一般取消）:**
- 使用 `expiration_date`（如果为空则使用 `cancellation_date`）
- 使用日历日（Calendar Days）
- **Stage 0 → Stage 1**: 下次拨打日期 = `expiration_date - 7天`
- **Stage 1 → Stage 2**: 下次拨打日期 = `expiration_date - 3天`
- **Stage 2**: 无更多跟进（已完成所有电话）

**Non-Payment Cancellation（未付款取消）:**
- 使用 `f_u_date` 和 `cancellation_date`
- 使用工作日（Business Days）
- **Stage 0 → Stage 1**: 
  - 计算总工作日数：`count_business_days(f_u_date, cancellation_date)`
  - 目标天数 = 总工作日数 / 3（至少1天）
  - 下次拨打日期 = `add_business_days(f_u_date, target_days)`
- **Stage 1 → Stage 2**:
  - 计算剩余工作日数：`count_business_days(f_u_date, cancellation_date)`
  - 目标天数 = 剩余工作日数 / 2（至少1天）
  - 下次拨打日期 = `add_business_days(f_u_date, target_days)`
- **Stage 2**: 无更多跟进（已完成所有电话）

#### English Logic

**General Cancellation:**
- Uses `expiration_date` (or `cancellation_date` if empty)
- Uses calendar days
- **Stage 0 → Stage 1**: Next call date = `expiration_date - 7 days`
- **Stage 1 → Stage 2**: Next call date = `expiration_date - 3 days`
- **Stage 2**: No more follow-ups (all calls completed)

**Non-Payment Cancellation:**
- Uses `f_u_date` and `cancellation_date`
- Uses business days
- **Stage 0 → Stage 1**: 
  - Calculate total business days: `count_business_days(f_u_date, cancellation_date)`
  - Target days = total business days / 3 (minimum 1 day)
  - Next call date = `add_business_days(f_u_date, target_days)`
- **Stage 1 → Stage 2**:
  - Calculate remaining business days: `count_business_days(f_u_date, cancellation_date)`
  - Target days = remaining business days / 2 (minimum 1 day)
  - Next call date = `add_business_days(f_u_date, target_days)`
- **Stage 2**: No more follow-ups (all calls completed)

---

## 拨打执行逻辑 / Call Execution Logic

### Stage 0 - 批量拨打模式 / Batch Calling Mode

#### 中文逻辑

1. **调用 VAPI 服务 / Call VAPI Service**
   ```python
   results = vapi_service.make_batch_call_with_assistant(
       customers,              # 所有 Stage 0 客户
       assistant_id,           # CANCELLATION_1ST_REMINDER_ASSISTANT_ID
       schedule_immediately=(schedule_at is None),
       schedule_at=schedule_at
   )
   ```

2. **处理结果 / Process Results**
   - 检查结果数量是否与客户数量匹配
   - 如果结果数量不匹配，显示警告

3. **更新 Smartsheet / Update Smartsheet**
   - 遍历每个客户和对应的 call_data
   - 如果 call_data 中没有 `analysis`，尝试刷新 call status
   - 调用 `update_after_call()` 更新 Smartsheet

#### English Logic

1. **Call VAPI Service**
   ```python
   results = vapi_service.make_batch_call_with_assistant(
       customers,              # All Stage 0 customers
       assistant_id,           # CANCELLATION_1ST_REMINDER_ASSISTANT_ID
       schedule_immediately=(schedule_at is None),
       schedule_at=schedule_at
   )
   ```

2. **Process Results**
   - Check if result count matches customer count
   - If counts don't match, display warning

3. **Update Smartsheet**
   - Iterate through each customer and corresponding call_data
   - If call_data doesn't have `analysis`, try refreshing call status
   - Call `update_after_call()` to update Smartsheet

### Stage 1 & 2 - 顺序拨打模式 / Sequential Calling Mode

#### 中文逻辑

1. **遍历每个客户 / Iterate Each Customer**
   ```python
   for i, customer in enumerate(customers, 1):
       # 拨打单个客户
       results = vapi_service.make_batch_call_with_assistant(
           [customer],        # 只有一个客户
           assistant_id,
           schedule_immediately=(schedule_at is None),
           schedule_at=schedule_at
       )
   ```

2. **处理结果 / Process Results**
   - 获取第一个（也是唯一的）结果
   - 如果成功，调用 `update_after_call()` 更新 Smartsheet
   - 如果失败，记录失败并继续下一个客户

#### English Logic

1. **Iterate Each Customer**
   ```python
   for i, customer in enumerate(customers, 1):
       # Call single customer
       results = vapi_service.make_batch_call_with_assistant(
           [customer],        # Only one customer
           assistant_id,
           schedule_immediately=(schedule_at is None),
           schedule_at=schedule_at
       )
   ```

2. **Process Results**
   - Get first (and only) result
   - If successful, call `update_after_call()` to update Smartsheet
   - If failed, log failure and continue to next customer

---

## 更新逻辑 / Update Logic

### 函数：`update_after_call(smartsheet_service, customer, call_data, current_stage)`

#### 中文逻辑说明

1. **提取通话分析 / Extract Call Analysis**
   ```python
   analysis = call_data.get('analysis', {})
   summary = analysis.get('summary', '')
   evaluation = analysis.get('successEvaluation', '')
   ```

2. **检查是否为语音邮件 / Check if Voicemail**
   ```python
   ended_reason = call_data.get('endedReason', '')
   is_voicemail = (ended_reason == 'voicemail')
   ```

3. **确定新阶段 / Determine New Stage**
   ```python
   new_stage = current_stage + 1
   ```

4. **计算下次跟进日期 / Calculate Next Follow-up Date**
   ```python
   next_followup_date = calculate_next_followup_date(customer, current_stage)
   ```

5. **格式化通话记录 / Format Call Notes**
   - 格式要求：
     ```
     Call Placed At: YYYY-MM-DD HH:MM:SS
     
     Did Client Answer: Yes/No
     
     Was Full Message Conveyed: Yes/No
     
     Was Voicemail Left: Yes/No
     
     analysis:
     
     {summary}
     ```

6. **更新字段 / Update Fields**
   ```python
   updates = {
       'ai_call_stage': new_stage,
       'ai_call_summary': new_ai_call_summary,
       'ai_call_eval': new_eval
   }
   if next_followup_date:
       updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')
   ```

7. **执行更新 / Execute Update**
   ```python
   success = smartsheet_service.update_customer_fields(customer, updates)
   ```

#### English Logic Description

1. **Extract Call Analysis**
   ```python
   analysis = call_data.get('analysis', {})
   summary = analysis.get('summary', '')
   evaluation = analysis.get('successEvaluation', '')
   ```

2. **Check if Voicemail**
   ```python
   ended_reason = call_data.get('endedReason', '')
   is_voicemail = (ended_reason == 'voicemail')
   ```

3. **Determine New Stage**
   ```python
   new_stage = current_stage + 1
   ```

4. **Calculate Next Follow-up Date**
   ```python
   next_followup_date = calculate_next_followup_date(customer, current_stage)
   ```

5. **Format Call Notes**
   - Required format:
     ```
     Call Placed At: YYYY-MM-DD HH:MM:SS
     
     Did Client Answer: Yes/No
     
     Was Full Message Conveyed: Yes/No
     
     Was Voicemail Left: Yes/No
     
     analysis:
     
     {summary}
     ```

6. **Update Fields**
   ```python
   updates = {
       'ai_call_stage': new_stage,
       'ai_call_summary': new_ai_call_summary,
       'ai_call_eval': new_eval
   }
   if next_followup_date:
       updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')
   ```

7. **Execute Update**
   ```python
   success = smartsheet_service.update_customer_fields(customer, updates)
   ```

---

## 手动拨打脚本 / Manual Calling Script

### 文件位置 / File Location
- `scripts/manual_cl1_calling.py` - 手动拨打脚本

### 函数：`manual_cl1_calling()`

#### 中文逻辑说明

1. **获取目标日期 / Get Target Date**
   - 如果提供了 `target_date_str`，解析该日期
   - 否则，提示用户输入日期（格式：YYYY-MM-DD）

2. **获取已过期客户 / Get Expired Customers**
   ```python
   expired_customers = get_customers_by_fu_date(smartsheet_service, target_date)
   ```
   - 筛选条件：
     - `f_u_date == target_date`
     - `cancellation_date <= f_u_date`（已过期）
     - `amount_due` 不为空
     - `done?` 未勾选
     - `stage < 3`（未完成所有电话）

3. **使用固定 Assistant ID / Use Fixed Assistant ID**
   ```python
   EXPIRED_POLICY_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"
   ```
   - 所有过期保单使用同一个 Assistant ID

4. **批量拨打 / Batch Call**
   ```python
   results = vapi_service.make_batch_call_with_assistant(
       expired_customers,
       EXPIRED_POLICY_ASSISTANT_ID,
       schedule_immediately=True
   )
   ```

5. **更新 Smartsheet / Update Smartsheet**
   - 对每个成功拨打的客户，调用 `update_after_call()` 更新

#### English Logic Description

1. **Get Target Date**
   - If `target_date_str` provided, parse that date
   - Otherwise, prompt user to input date (format: YYYY-MM-DD)

2. **Get Expired Customers**
   ```python
   expired_customers = get_customers_by_fu_date(smartsheet_service, target_date)
   ```
   - Filter conditions:
     - `f_u_date == target_date`
     - `cancellation_date <= f_u_date` (expired)
     - `amount_due` is not empty
     - `done?` is not checked
     - `stage < 3` (not all calls completed)

3. **Use Fixed Assistant ID**
   ```python
   EXPIRED_POLICY_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"
   ```
   - All expired policies use the same Assistant ID

4. **Batch Call**
   ```python
   results = vapi_service.make_batch_call_with_assistant(
       expired_customers,
       EXPIRED_POLICY_ASSISTANT_ID,
       schedule_immediately=True
   )
   ```

5. **Update Smartsheet**
   - For each successfully called customer, call `update_after_call()` to update

---

## 关键验证逻辑 / Key Validation Logic

### 函数：`should_skip_row(customer)`

#### 中文逻辑

1. **检查 done 复选框 / Check Done Checkbox**
   - 如果 `done?` 为 `True`，跳过

2. **检查状态 / Check Status**
   - 如果 `Status` 为 "Paid"，跳过

3. **根据取消类型检查 / Check Based on Cancellation Type**

   **General Cancellation:**
   - 不需要 `amount_due`
   - 需要 `expiration_date` 或 `cancellation_date`（至少一个不为空）

   **Non-Payment Cancellation:**
   - 需要 `amount_due`（不为空）
   - 需要 `cancellation_date`（不为空）
   - **注意**：已移除日期关系检查（`cancellation_date > f_u_date`）
   - 如果 `f_u_date == today`，必须拨打，无论日期关系如何

#### English Logic

1. **Check Done Checkbox**
   - If `done?` is `True`, skip

2. **Check Status**
   - If `Status` is "Paid", skip

3. **Check Based on Cancellation Type**

   **General Cancellation:**
   - No `amount_due` required
   - Requires `expiration_date` or `cancellation_date` (at least one not empty)

   **Non-Payment Cancellation:**
   - Requires `amount_due` (not empty)
   - Requires `cancellation_date` (not empty)
   - **Note**: Date relationship check (`cancellation_date > f_u_date`) has been removed
   - If `f_u_date == today`, must call regardless of date relationship

---

## 总结 / Summary

### 中文

CL1 项目的拨打电话逻辑是一个完整的三阶段自动化系统：

1. **自动触发**: 每天在太平洋时间 11:00 AM 和 4:00 PM 自动运行
2. **智能筛选**: 根据取消类型、日期、阶段等多重条件筛选客户
3. **分阶段拨打**: Stage 0 批量拨打，Stage 1-2 顺序拨打
4. **自动更新**: 每次拨打后自动更新 Smartsheet 中的阶段、摘要和下次跟进日期
5. **手动支持**: 提供手动拨打脚本，支持按 F/U Date 批量拨打过期保单

### English

The CL1 project's dial phone logic is a complete three-stage automated system:

1. **Auto Trigger**: Automatically runs daily at 11:00 AM and 4:00 PM Pacific Time
2. **Smart Filtering**: Filters customers based on cancellation type, dates, stages, and multiple conditions
3. **Staged Calling**: Stage 0 batch calling, Stage 1-2 sequential calling
4. **Auto Update**: Automatically updates stage, summary, and next follow-up date in Smartsheet after each call
5. **Manual Support**: Provides manual calling script supporting batch calling of expired policies by F/U Date

---

## 相关文件 / Related Files

- `main.py` - 主入口文件
- `workflows/cancellations.py` - 核心工作流逻辑
- `scripts/manual_cl1_calling.py` - 手动拨打脚本
- `config/settings.py` - 配置文件（Assistant IDs, Sheet IDs）
- `services/vapi_service.py` - VAPI 服务接口
- `services/smartsheet_service.py` - Smartsheet 服务接口

