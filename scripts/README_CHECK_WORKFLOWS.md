# 📋 检查 Workflow 执行状态指南

## 方法 1: 使用 GitHub API 脚本（推荐）

### 步骤 1: 获取 GitHub Token

1. 访问 https://github.com/settings/tokens
2. 点击 **"Generate new token (classic)"**
3. 输入 token 名称（如 "Workflow Checker"）
4. 选择权限：
   - ✅ `repo` (完整仓库访问权限)
5. 点击 **"Generate token"**
6. **复制 token**（只显示一次，请保存好）

### 步骤 2: 运行查询脚本

**PowerShell:**
```powershell
# 方式 1: 使用环境变量
$env:GITHUB_TOKEN="your_token_here"
python scripts/check_github_actions_status.py

# 方式 2: 使用命令行参数
python scripts/check_github_actions_status.py --token your_token_here

# 方式 3: 检查指定日期
python scripts/check_github_actions_status.py --token your_token_here --date 2025-12-05
```

**命令提示符 (CMD):**
```cmd
set GITHUB_TOKEN=your_token_here
python scripts/check_github_actions_status.py
```

### 步骤 3: 查看结果

脚本会显示：
- ✅ CL1 和 N1 workflow 的执行状态
- 📅 运行时间
- 🔗 详细日志链接
- 📊 执行结果（成功/失败/跳过）

---

## 方法 2: 直接在 GitHub 网站查看

### 步骤 1: 打开 GitHub 仓库

访问: https://github.com/Across-America/python-read-write-sheet

### 步骤 2: 查看 Actions

1. 点击 **"Actions"** 标签
2. 在左侧选择要查看的 workflow：
   - **"Daily Cancellation Workflow"** (CL1 Project)
   - **"Daily Renewal Workflow"** (N1 Project)

### 步骤 3: 查找上周五的运行记录

1. 在运行历史中找到 **2025-12-05** 的记录
2. 点击查看详细日志
3. 检查：
   - ✅ 运行状态（绿色 = 成功，红色 = 失败，黄色 = 跳过）
   - 📅 运行时间（应该在太平洋时间 4:00 PM 左右）
   - 📝 日志内容

---

## 方法 3: 使用本地日志检查

```powershell
python scripts/check_last_friday_workflows.py
```

注意：本地日志可能不完整，因为 workflow 在 GitHub Actions 上运行。

---

## 常见问题

### Q: 为什么找不到运行记录？

**可能原因：**
1. **时间检查**: Python 代码会检查是否是太平洋时间 4:00 PM，如果不是会跳过
2. **周末**: Workflow 不会在周末运行
3. **没有符合条件的客户**: 如果没有需要拨打的客户，workflow 可能不会产生运行记录
4. **日期计算**: 时区差异可能导致日期不匹配

### Q: Workflow 显示 "skipped"？

这是正常的，如果：
- 不是太平洋时间 4:00 PM
- 是周末
- 没有符合条件的客户

### Q: 如何查看详细日志？

点击 GitHub Actions 运行记录中的 **"Run cancellation workflow"** 或 **"Run renewal workflow"**，查看完整的执行日志。

---

## 快速检查命令

```powershell
# 检查上周五（自动计算）
python scripts/check_github_actions_status.py --token YOUR_TOKEN

# 检查指定日期
python scripts/check_github_actions_status.py --token YOUR_TOKEN --date 2025-12-05

# 检查本地日志
python scripts/check_last_friday_workflows.py
```

