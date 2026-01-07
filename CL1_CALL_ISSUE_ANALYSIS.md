# CL1 项目电话拨打问题分析报告

## 问题描述

团队询问：为什么取消保单的 Smartsheet 中，大部分客户没有接到电话？只有 Jaspinder 接到了电话，而且同一天接到了两次电话。

## 诊断结果

### 主要问题

1. **35 个客户的 `cancellation_reason` 字段为空**
   - 这些客户被分类为 "other" 类型
   - "other" 类型的客户在 `get_customers_ready_for_calls()` 函数中被跳过
   - 代码只支持 "general" 和 "non_payment" 两种类型

2. **只有 1 个客户今天接到了电话**
   - Row 59 (可能是 Jaspinder): Non-Payment 类型
   - 今天有 1 次通话记录（但用户说看到了两次，可能是显示问题或批量更新脚本的问题）

### 详细统计

- **总客户数**: 62
- **Non-Payment 类型**: 24 个客户（有 `cancellation_reason = "Non-Payment"`）
- **General 类型**: 3 个客户（有 `cancellation_reason = "UW Reason"`）
- **Unknown/Other 类型**: 35 个客户（`cancellation_reason` 为空或不符合模式）

### 其他跳过原因

- **Status = "Paid"**: 8 个客户（已付款，不需要拨打）
- **Done checkbox checked**: 5 个客户
- **Amount Due 为空**: 5 个客户（Non-Payment 类型需要）
- **日期关系问题**: 多个客户的 Cancellation Date <= F/U Date（不符合逻辑）

## 为什么没有拨打？

### 根本原因

**35 个客户的 `cancellation_reason` 字段为空**，导致：

1. `get_cancellation_type()` 函数返回 `'other'`
2. 在 `get_customers_ready_for_calls()` 中，`cancellation_type == 'other'` 的客户被跳过：
   ```python
   if cancellation_type == 'other':
       skipped_count += 1
       print(f"   ⏭️  Skipping row {customer.get('row_number')}: Unknown cancellation type")
       continue
   ```

### 代码逻辑

当前代码只识别以下取消原因：

**General 类型**:
- "UW Reason"
- "Underwriter Declined"  
- "Unresponsive Insured"
- （注释中提到 "Client Requested Cancellation" 但代码中没有实现）

**Non-Payment 类型**:
- "Non-Payment"
- "NonPayment"

**其他所有情况**: 被分类为 "other" 并跳过

## 为什么 Jaspinder 接到了电话？

Row 59 的客户（可能是 Jaspinder）：
- `cancellation_reason = "Non-Payment"` ✅
- 类型正确识别为 `non_payment` ✅
- 符合所有拨打条件 ✅
- 所以接到了电话

## 为什么 Jaspinder 接到了两次电话？

可能的原因：

1. **批量更新脚本运行了多次**
   - `batch_update_missing_call_notes.py` 可能被运行了多次
   - 每次运行都会检查 VAPI 的通话记录并更新 Smartsheet

2. **`was_called_today()` 函数可能没有正确检测到之前的通话**
   - 函数通过解析 `ai_call_summary` 字段来检测
   - 如果字段格式不正确或更新延迟，可能检测失败

3. **手动触发了电话**
   - 可能有人手动运行了 `manual_cl1_calling.py` 脚本

## 解决方案

### 方案 1: 修复数据（推荐）

**在 Smartsheet 中为所有客户填写 `cancellation_reason` 字段**

- 如果客户是 Non-Payment，填写 "Non-Payment"
- 如果客户是其他原因，填写 "UW Reason" 或其他支持的 General 类型原因

### 方案 2: 更新代码逻辑

**修改 `get_cancellation_type()` 函数，处理空值情况**

选项 A: 如果 `cancellation_reason` 为空，根据其他字段推断类型
```python
def get_cancellation_type(customer):
    cancellation_reason = str(customer.get('cancellation_reason', '') or customer.get('cancellation reason', '')).strip().lower()
    
    # 如果取消原因为空，尝试根据其他字段推断
    if not cancellation_reason:
        # 如果有 amount_due，可能是 Non-Payment
        if customer.get('amount_due', '').strip():
            return 'non_payment'
        # 否则默认为 general
        return 'general'
    
    # ... 现有逻辑 ...
```

选项 B: 如果 `cancellation_reason` 为空，默认使用 Non-Payment 逻辑（如果有 amount_due）
```python
def get_cancellation_type(customer):
    cancellation_reason = str(customer.get('cancellation_reason', '') or customer.get('cancellation reason', '')).strip().lower()
    
    # 如果取消原因为空，根据 amount_due 判断
    if not cancellation_reason:
        if customer.get('amount_due', '').strip():
            return 'non_payment'
        else:
            return 'general'  # 默认使用 general 逻辑
    
    # ... 现有逻辑 ...
```

### 方案 3: 支持更多取消原因

**扩展 `get_cancellation_type()` 函数以支持更多取消原因**

例如：
- "Client Requested Cancellation" → general
- "Underwriter" → general
- "Unresponsive" → general
- 等等

## 建议

1. **立即行动**: 检查 Smartsheet 中这 35 个客户的 `cancellation_reason` 字段，填写正确的值

2. **代码改进**: 更新代码以更好地处理空值情况，避免因为数据不完整而跳过客户

3. **防止重复拨打**: 检查 `was_called_today()` 函数，确保正确检测同一天的通话

4. **数据验证**: 添加数据验证，确保新添加的客户都有 `cancellation_reason`

## 相关文件

- `workflows/cancellations.py` - 主要逻辑
- `scripts/check_cl1_today.py` - 检查脚本
- `scripts/diagnose_cancellation_calls.py` - 诊断脚本（新创建）
- `scripts/batch_update_missing_call_notes.py` - 批量更新脚本

## 下一步

1. 运行 `python scripts/diagnose_cancellation_calls.py` 查看详细分析
2. 检查 Smartsheet 中客户的 `cancellation_reason` 字段
3. 根据实际情况选择解决方案（修复数据或更新代码）




