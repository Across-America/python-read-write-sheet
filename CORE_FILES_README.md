# 核心文件说明

## 📞 批量呼叫系统核心文件

### 主要脚本

#### 1. **test_batch_call_not_called.py** ⭐ 主要使用
完整的批量呼叫系统，用于呼叫所有 "Not call yet" 状态的客户
- ✅ 自动从 Smartsheet 获取 "Not call yet" 客户
- ✅ 使用 VAPI batch calling API 并行呼叫
- ✅ 自动更新 Call Status 和 Call Result
- ✅ 包含详细的 VAPI 分析结果
- ✅ 支持单个客户测试和批量呼叫
- **推荐使用场景**: 主要的批量呼叫工作流

#### 2. **test_batch_call_auto.py** ⭐ 自动批量呼叫
自动批量呼叫系统，无需用户交互
- ✅ 自动呼叫所有 "Not call yet" 客户
- ✅ 3秒倒计时后自动开始
- ✅ 更新所有客户的 Call Result
- **推荐使用场景**: 自动化批量呼叫任务

### 工具脚本

#### 3. **update_all_call_results.py** 🔧 批量更新工具
批量更新所有客户的 Call Result
- 从 VAPI 获取所有呼叫记录
- 匹配 Smartsheet 中的客户（通过电话号码）
- 更新所有已呼叫客户的详细分析结果
- **推荐使用场景**: 修复或更新已有呼叫的分析结果

#### 4. **fix_incomplete_call_results.py** 🔧 修复工具
修复不完整的 Call Results
- 查找 "Called" 状态但 Call Result 不完整的客户
- 从 VAPI 获取最新的呼叫分析
- 更新为完整的分析结果
- **推荐使用场景**: 修复批量呼叫后未正确更新的记录

#### 5. **update_no_answer_results.py** 🔧 未接听更新工具
为未接听的客户设置适当的 Call Result
- 查找只有基本信息的 Call Result
- 根据呼叫结束原因设置适当的结果
- 区分客户未接听、静默超时等情况
- **推荐使用场景**: 更新未接听客户的呼叫结果

#### 6. **update_vapi_analysis_plan.py** ⚙️ 配置工具
更新 VAPI assistant 的分析计划配置
- 配置 structuredDataPlan（结构化数据提取）
- 配置 successEvaluationPlan（成功评估）
- **推荐使用场景**: 一次性配置，修改 VAPI 分析规则时使用

### 原始文件（保留）

#### 7. **main.py**
原始的批量呼叫系统入口文件
- 保留用于参考
- 不推荐直接使用

#### 8. **python-read-write-sheet.py**
原始的 Smartsheet 读写示例
- 保留用于参考
- 不推荐直接使用

---

## 🚀 推荐工作流

### 日常批量呼叫
1. 运行 `test_batch_call_not_called.py`
2. 选择选项 2（批量呼叫所有客户）
3. 确认后系统自动呼叫所有 "Not call yet" 客户
4. 自动更新 Call Status 和 Call Result

### 自动化批量呼叫（无需交互）
1. 直接运行 `test_batch_call_auto.py`
2. 系统自动呼叫所有 "Not call yet" 客户
3. 所有更新自动完成

### 修复呼叫结果
1. 如果发现某些客户的 Call Result 不完整
2. 运行 `fix_incomplete_call_results.py`
3. 系统自动修复所有不完整的记录

### 批量更新所有呼叫分析
1. 如果需要重新更新所有呼叫的分析结果
2. 运行 `update_all_call_results.py`
3. 系统从 VAPI 获取所有呼叫并更新 Smartsheet

---

## 📁 目录结构

```
python-read-write-sheet/
├── test_batch_call_not_called.py    # ⭐ 主要批量呼叫脚本
├── test_batch_call_auto.py          # ⭐ 自动批量呼叫脚本
├── update_all_call_results.py       # 🔧 批量更新工具
├── fix_incomplete_call_results.py   # 🔧 修复不完整结果工具
├── update_no_answer_results.py      # 🔧 未接听结果更新工具
├── update_vapi_analysis_plan.py     # ⚙️ VAPI配置工具
├── core/                            # 核心模块
│   ├── auto_call_and_update.py
│   ├── batch_call_system.py
│   └── make_vapi_call.py
├── tools/                           # 工具脚本
│   ├── explore_cancellations.py
│   ├── find_phone_demo.py
│   ├── update_call_result.py
│   └── verify_phone_number.py
└── utils/                           # 工具函数
    ├── vapi_fields_config.py
    └── vapi_prompt_templates.py
```

---

## ⚠️ 注意事项

1. **环境变量**: 确保 `.env` 文件包含正确的 API keys
2. **VAPI Assistant ID**: 使用 Spencer: Call Transfer V2 Campaign (8e07049e-f7c8-4e5d-a893-8c33a318490d)
3. **公司来电显示**: 所有呼叫都使用 +1 (951) 247-2003
4. **Smartsheet Sheet ID**: Cancellation Dev (5146141873098628)
5. **费用**: 每次呼叫都会产生费用，请谨慎使用

---

## 📝 Call Result 格式

详细的 Call Result 包含以下信息：
- **CALL COMPLETED**: 呼叫状态
- **SUMMARY**: 呼叫摘要
- **TRANSFER REQUESTED/SUCCESSFULLY TRANSFERRED**: 转接状态
- **CUSTOMER ENDED CALL**: 客户结束呼叫
- **PAYMENT CLAIMED**: 客户声称的付款状态
- **CONCERNS**: 客户的疑虑
- **CUSTOMER UNDERSTOOD/ENGAGED**: 通话质量指标
- **CALLBACK REQUESTED/ESCALATION NEEDED**: 后续跟进需求
- **EVALUATION**: 成功评估（SUCCESS/UNSUCCESSFUL）
- **DURATION**: 通话时长
- **COST**: 呼叫费用

---

## 🔗 相关文档

- `BATCH_CALL_GUIDE.md` - 批量呼叫使用指南
- `VAPI_SETUP_GUIDE.md` - VAPI 配置指南
- `VAPI_ANALYSIS_PLAN_CONFIG.md` - VAPI 分析计划配置


