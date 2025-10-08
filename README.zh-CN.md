# AAIS 自动化工作流系统

> **多语言文档**: [English](README.md) | [中文](README.zh-CN.md) | [Español](README.es.md)

基于 VAPI 和 Smartsheet 集成的自动化呼叫工作流系统。支持多种工作流类型，具备智能调度和时区处理功能。

## 功能特性

- **多工作流支持**: 取消提醒、账单通知等多种工作流
- **三阶段呼叫系统**: 自动跟进序列，每个阶段使用专属 AI 助手
- **智能调度**: 工作日计算，自动处理夏令时切换
- **批量与顺序呼叫**: Stage 0 批量呼叫，Stage 1-2 顺序呼叫
- **Smartsheet 集成**: 自动更新记录和呼叫跟踪
- **GitHub Actions**: 无服务器部署，每日自动执行

## 项目结构

```
.
├── config/              # 配置文件
├── services/            # 外部API服务
│   ├── smartsheet_service.py
│   └── vapi_service.py
├── workflows/           # 业务流程
│   └── cancellations.py
├── utils/              # 工具函数
├── tests/              # 测试文件
├── main.py             # 入口文件（cron job）
└── .env               # 环境变量
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（只需配置2个关键变量）：

```env
SMARTSHEET_ACCESS_TOKEN=your_token
VAPI_API_KEY=your_vapi_key
```

**其他配置在 `config/settings.py` 中**：
- `CANCELLATION_SHEET_ID` - Smartsheet ID
- `COMPANY_PHONE_NUMBER_ID` - 公司来电显示号码
- `CANCELLATION_1ST/2ND/3RD_REMINDER_ASSISTANT_ID` - 三个阶段的 Assistant ID
- `TEST_CUSTOMER_PHONE` - 测试电话号码

### 3. 运行测试

```bash
python3 tests/test_vapi_cancellation_flow.py
```

### 4. 手动运行

```bash
python3 main.py
```

## 部署方式

### ✅ 推荐：GitHub Actions（免费且自动）

系统已配置 GitHub Actions 自动运行，**无需额外服务器**！

#### 1. 设置 GitHub Secrets

在你的 GitHub repository：

1. 进入 **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**
3. 添加以下两个 secrets：
   - Name: `SMARTSHEET_ACCESS_TOKEN`，Value: 你的 Smartsheet token
   - Name: `VAPI_API_KEY`，Value: 你的 VAPI API key

#### 2. 启用 GitHub Actions

1. 进入 **Actions** 标签页
2. 找到 "Daily Cancellation Workflow"
3. 点击 **Enable workflow**（如果需要）

#### 3. 验证运行

- **自动运行**：每天 UTC 23:00（PST 4:00 PM）自动触发
- **手动运行**：Actions → Daily Cancellation Workflow → Run workflow
- **查看日志**：Actions → 点击任意运行记录查看详细日志

#### 时区说明

- 夏令时（3月-11月）：UTC 23:00 = PST 4:00 PM ✅
- 标准时间（11月-3月）：需要改为 UTC 0:00 = PST 4:00 PM
- 修改方法：编辑 `.github/workflows/daily-cancellation.yml` 中的 cron 时间

### 备选：传统服务器部署（不推荐）

<details>
<summary>点击展开服务器部署方式（仅在特殊情况下使用）</summary>

#### 1. 上传代码

```bash
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  . user@server:/opt/aais/python-read-write-sheet/
```

#### 2. 安装依赖

```bash
ssh user@server
cd /opt/aais/python-read-write-sheet
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 设置定时任务

```bash
crontab -e
```

添加：
```cron
0 16 * * * TZ=America/Los_Angeles cd /opt/aais/python-read-write-sheet && /opt/aais/python-read-write-sheet/venv/bin/python3 main.py >> logs/cron/output.log 2>&1
```

</details>

## 测试

所有测试文件在 `tests/` 目录：

- `test_vapi_cancellation_flow.py` - 完整端到端测试
- `test_followup_date_calculation.py` - 日期计算测试
- `cleanup_test_data.py` - 清理测试数据

## 工作流程

### 每日自动运行流程

1. **每天PST 4:00 PM** - Cron任务触发
2. **筛选客户** - 获取今天需要拨打的客户（`f_u_date` = 今天）
3. **Stage 0（第1次提醒）** - 批量拨打初次提醒
4. **Stage 1-2（第2-3次提醒）** - 顺序拨打后续提醒
5. **更新记录** - 写入通话结果和下次F/U日期
6. **等待人工确认** - Stage 3 完成后不自动标记 done，等待人工检查
7. **自动清理** - 30天后自动删除旧日志

### 客户筛选规则

**跳过以下情况**：
- `done?` 已勾选
- `company` 为空
- `amount_due` 为空
- `cancellation_date` 为空
- `ai_call_stage >= 3`（已完成3次电话）

**拨打条件**：
- `f_u_date`（跟进日期）= 今天

### 三阶段流程详解

#### **Stage 0 → 1（第1次提醒）**
- Smartsheet 中 `ai_call_stage` = 空或0
- 使用 `CANCELLATION_1ST_REMINDER_ASSISTANT_ID`
- **批量拨打**（所有客户同时）
- 计算下次F/U日期 = 当前 + (总工作日 ÷ 3)
- 更新 Smartsheet：`ai_call_stage = 1`

#### **Stage 1 → 2（第2次提醒）**
- Smartsheet 中 `ai_call_stage = 1`
- 使用 `CANCELLATION_2ND_REMINDER_ASSISTANT_ID`
- **顺序拨打**（一个一个打）
- 计算下次F/U日期 = 当前 + (剩余工作日 ÷ 2)
- 更新 Smartsheet：`ai_call_stage = 2`

#### **Stage 2 → 3（第3次提醒）**
- Smartsheet 中 `ai_call_stage = 2`
- 使用 `CANCELLATION_3RD_REMINDER_ASSISTANT_ID`
- **顺序拨打**（一个一个打）
- 无下次F/U日期
- 更新 Smartsheet：`ai_call_stage = 3`
- **不自动标记 done** - 等待人工检查后确认

### 工作日计算

- 自动跳过周六/周日
- F/U日期保证落在工作日
- 所有日期计算排除周末

### 更新字段

每次通话后更新：
- `ai_call_stage`: +1
- `ai_call_summary`: 追加通话摘要
- `ai_call_eval`: 追加评估结果
- `f_u_date`: 下次跟进日期（Stage 3 后为空）
- ~~`done?`~~: 已禁用自动标记，等待人工检查

## 日志

日志存储在 `logs/cron/` 目录：
- `cancellations_YYYY-MM-DD.log` - 每日运行日志
- `output.log` - Cron输出
- 自动保留30天

## 故障排查

查看日志：
```bash
tail -f logs/cron/output.log
```

手动测试：
```bash
source venv/bin/activate
python3 main.py
```

## 技术栈

- Python 3.8+
- Smartsheet API
- VAPI API
- Cron (定时任务)
