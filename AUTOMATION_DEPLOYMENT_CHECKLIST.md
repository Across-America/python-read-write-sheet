# 🚀 Renewal Workflow 自动化部署检查清单

## ✅ 当前状态

- [x] Renewal Workflow 代码已完成
- [x] 功能测试通过（包括 Last Call Made Date）
- [x] GitHub Actions workflow 文件已创建 (`.github/workflows/daily-renewal.yml`)
- [x] 部署文档已准备

## 📋 部署步骤

### 步骤 1: 确认 GitHub Secrets（必须）

1. 进入 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 确认以下 Secrets 存在：
   - ✅ `SMARTSHEET_ACCESS_TOKEN`
   - ✅ `VAPI_API_KEY`

如果还没有，点击 **New repository secret** 添加。

### 步骤 2: 提交并推送代码

```bash
# 检查当前状态
git status

# 添加所有更改的文件
git add .

# 提交（包含 Last Call Made Date 功能）
git commit -m "Complete Renewal Workflow with Last Call Made Date feature

- Add Last Call Made Date column support
- Update workflows/renewals.py to record call dates
- Test and verify all functionality"

# 推送到 GitHub
git push origin master
```

### 步骤 3: 验证 GitHub Actions Workflow

1. 进入 GitHub 仓库
2. 点击 **Actions** 标签
3. 应该看到 **"Daily Renewal Workflow"**
4. 点击 **"Run workflow"** 手动触发一次测试

### 步骤 4: 测试手动触发

1. 在 GitHub Actions 页面
2. 选择 **"Daily Renewal Workflow"**
3. 点击 **"Run workflow"** 按钮
4. 选择分支（通常是 `master`）
5. 点击 **"Run workflow"**
6. 等待运行完成，检查日志

### 步骤 5: 验证自动运行

Workflow 会在每天**太平洋时间 4:00 PM**自动运行：
- 夏令时 (PDT): UTC 23:00
- 标准时间 (PST): UTC 00:00

第二天检查是否自动运行成功。

## 📊 运行后验证

### 检查 GitHub Actions 日志

1. 进入 **Actions** 标签
2. 点击最新的运行记录
3. 检查：
   - ✅ 运行状态（绿色 = 成功）
   - ✅ 运行日志（查看是否有错误）
   - ✅ 运行时间（应该是 4:00 PM Pacific）

### 检查 Smartsheet

打开 "11. November PLR" sheet，验证：
- ✅ **Last Call Made Date** 列已更新（日期格式：YYYY-MM-DD）
- ✅ **Call Notes** 列有新的通话记录
- ✅ **Stage** 列已更新
- ✅ **F/U Date** 列已更新

## ⚠️ 注意事项

### 1. Secrets 必须配置
如果没有配置 Secrets，workflow 会失败。错误信息会显示在 GitHub Actions 日志中。

### 2. 时区处理
- Workflow 会在两个 UTC 时间运行（23:00 和 00:00）
- Python 代码会自动检查是否是太平洋时间 4:00 PM
- 如果不是 4:00 PM，会跳过运行（这是正常的）

### 3. 手动触发
- 手动触发时，会跳过时间检查，立即运行
- 适合测试和紧急情况

### 4. 运行环境
- Workflow 在 GitHub 的 Ubuntu 服务器上运行
- 不需要你的本地电脑
- 24/7 自动运行

## 🔄 与 Cancellation Workflow 的关系

现在有两个独立的 workflow：

1. **Daily Cancellation Workflow** (`daily-cancellation.yml`)
   - 运行 CL1 Project - Cancellation
   - 每天 4:00 PM Pacific

2. **Daily Renewal Workflow** (`daily-renewal.yml`) ⭐
   - 运行 N1 Project - Renewal
   - 每天 4:00 PM Pacific
   - 包含 Last Call Made Date 功能

两个 workflow **可以同时运行**，互不干扰。

## ✅ 最终检查清单

部署完成后确认：
- [ ] GitHub Secrets 已配置（SMARTSHEET_ACCESS_TOKEN, VAPI_API_KEY）
- [ ] 代码已推送到 GitHub
- [ ] Workflow 文件存在于 `.github/workflows/daily-renewal.yml`
- [ ] 可以手动触发 workflow
- [ ] 手动触发运行成功
- [ ] 日志显示正常工作
- [ ] Smartsheet 数据正确更新（包括 Last Call Made Date）
- [ ] 等待第二天验证自动运行

## 🎯 下一步

1. **立即**: 完成上述步骤 1-4
2. **今天**: 手动触发一次测试运行
3. **明天**: 验证自动运行是否正常
4. **持续**: 监控运行历史和日志

**设置完成！Workflow 会自动每天运行！** 🚀

