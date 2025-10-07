# Multi-Stage Batch Calling System

## 概述

这是一个智能的3阶段呼叫系统，自动管理多次提醒呼叫，并智能计算工作日的后续跟进日期。

## 🆕 新文件

- `workflows/batch_calling_v2.py` - 新的多阶段呼叫系统
- `test_multi_stage.py` - 测试脚本
- `MULTI_STAGE_CALLING_README.md` - 本文档

## 📋 新增的 Smartsheet 列

| 列名 | 类型 | 说明 |
|------|------|------|
| `Company` | Text | 公司名称（必填） |
| `Amount Due` | Currency/Text | 欠款金额（必填） |
| `Cancellation Date` | Date | 取消日期（必填） |
| `Done?` | Checkbox | 是否完成 |
| `F/U Date` | Date | 跟进日期 |
| `AI Call Stage` | Number | 呼叫阶段 (0, 1, 2, 3) |
| `AI Summary` | Text/Long | 呼叫摘要（自动追加） |
| `AI Call Eval` | Text/Long | 呼叫评估（自动追加） |

## 🔄 呼叫阶段

### Stage 0: 第一次呼叫
- Assistant: `CANCELLATION_1ST_REMAINDER_ASSISTANT_ID`
- 后续日期: 原始日期 + (总工作日 × 1/3)

### Stage 1: 第二次呼叫  
- Assistant: `CANCELLATION_2ND_REMAINDER_ASSISTANT_ID`
- 后续日期: 当前日期 + (剩余工作日 × 1/2)

### Stage 2: 第三次呼叫（最终）
- Assistant: `CANCELLATION_3RD_REMAINDER_ASSISTANT_ID`
- 完成后设置 done=true，不再呼叫

## 🚀 使用方法

### 1. 测试系统
```bash
python3 test_multi_stage.py
```

### 2. 运行呼叫
```bash
python3 -c "from workflows.batch_calling_v2 import run_multi_stage_batch_calling; run_multi_stage_batch_calling()"
```

## ✨ 主要特性

✅ 智能阶段管理 - 自动跟踪每个客户的呼叫阶段
✅ 工作日感知 - 自动跳过周末
✅ 历史记录 - 追加而非覆盖
✅ 灵活的 Assistant - 每阶段不同脚本
✅ 自动完成 - 第3次后标记完成
✅ 数据验证 - 严格验证防止错误

## 📝 更新内容

### services/smartsheet_service.py
- ✅ 添加 `get_all_customers_with_stages()` - 获取所有客户含阶段信息
- ✅ 添加 `update_customer_fields()` - 更新多个字段
- ✅ 修复 checkbox 处理 - 正确读取 Done? 字段

### services/vapi_service.py
- ✅ 添加 `make_batch_call_with_assistant()` - 支持指定 assistant
- ✅ 修改 `__init__` 使 assistant_id 可选

### workflows/batch_calling_v2.py (新)
- ✅ 完整的多阶段呼叫逻辑
- ✅ 工作日计算函数
- ✅ 数据验证和过滤
- ✅ 自动字段更新

---

**创建日期:** 2025-10-06
**版本:** 2.0
