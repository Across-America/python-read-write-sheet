# 🚀 GitHub Actions 自动化设置

## ✅ 已创建的 Workflow

已创建以下 workflow 文件：
- `.github/workflows/daily-renewal.yml` - Renewal Workflow
- `.github/workflows/daily-non-renewal.yml` - Non-Renewal Workflow ⭐ 新增

所有 workflow 都与现有的 `daily-cancellation.yml` 类似。

## 📋 设置步骤

### 1. 确认 GitHub Secrets（必须）

在 GitHub 仓库中，确保已设置以下 Secrets：

1. 进入仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 确认以下 Secrets 存在：
   - ✅ `SMARTSHEET_ACCESS_TOKEN`
   - ✅ `VAPI_API_KEY`

如果还没有设置，点击 **New repository secret** 添加。

### 2. 推送代码到 GitHub

```bash
# 添加新文件
git add .github/workflows/daily-renewal.yml
git add .github/workflows/daily-non-renewal.yml
git add deploy_renewal.py
git add DEPLOYMENT_GUIDE.md
git add check_production_config.py
git add run_renewal_production.py

# 提交
git commit -m "Add Renewal and Non-Renewal Workflow deployment and GitHub Actions automation"

# 推送
git push origin master
```

### 3. 验证 Workflow

1. 进入 GitHub 仓库
2. 点击 **Actions** 标签
3. 应该看到以下 workflow：
   - "Daily Cancellation Workflow"
   - "Daily Renewal Workflow"
   - "Daily Non-Renewal Workflow" ⭐ 新增
4. 可以点击 **Run workflow** 手动触发一次测试

## ⏰ 运行时间

Workflow 会在每天**太平洋时间 4:00 PM**自动运行：
- 夏令时 (PDT): UTC 23:00
- 标准时间 (PST): UTC 00:00

Python 代码会自动检查时区，确保只在 4:00 PM 运行。

## 🖱️ 手动触发

如果需要立即运行（不等待定时任务）：

1. 进入 GitHub 仓库 → **Actions**
2. 选择要运行的 workflow（如 "Daily Non-Renewal Workflow"）
3. 点击 **Run workflow** 按钮
4. 选择分支（通常是 `master`）
5. 点击 **Run workflow**

## 📊 查看运行历史

1. 进入 **Actions** 标签
2. 选择要查看的 workflow（如 "Daily Non-Renewal Workflow"）
3. 查看每次运行的：
   - ✅ 运行状态（成功/失败）
   - ✅ 运行日志
   - ✅ 运行时间

## 🔄 所有 Workflow 的关系

现在有三个独立的 workflow：

1. **Daily Cancellation Workflow** (`daily-cancellation.yml`)
   - 运行 CL1 Project - Cancellation
   - 每天 4:00 PM Pacific

2. **Daily Renewal Workflow** (`daily-renewal.yml`)
   - 运行 N1 Project - Renewal
   - 每天 4:00 PM Pacific

3. **Daily Non-Renewal Workflow** (`daily-non-renewal.yml`) ⭐ 新增
   - 运行 N1 Project - Non-Renewal
   - 每天 4:00 PM Pacific

所有 workflow **可以同时运行**，互不干扰。

## ⚠️ 注意事项

### 1. Secrets 必须配置
如果没有配置 Secrets，workflow 会失败。

### 2. 时区处理
Workflow 会在两个 UTC 时间运行（23:00 和 00:00），但 Python 代码会检查是否是太平洋时间 4:00 PM，如果不是会跳过。

### 3. 手动触发
手动触发时，会跳过时间检查，立即运行。

### 4. 运行环境
Workflow 在 GitHub 的 Ubuntu 服务器上运行，不需要你的本地电脑。

## ✅ 验证 Checklist

部署后确认：
- [ ] GitHub Secrets 已配置
- [ ] 代码已推送到 GitHub
- [ ] Workflow 文件存在于 `.github/workflows/daily-renewal.yml`
- [ ] Workflow 文件存在于 `.github/workflows/daily-non-renewal.yml` ⭐
- [ ] 可以手动触发 workflow
- [ ] 手动触发运行成功
- [ ] 等待第二天验证自动运行

## 🎯 下一步

1. **立即**: 手动触发一次测试运行
2. **明天**: 验证自动运行是否正常
3. **持续**: 监控运行历史和日志

**设置完成！Workflow 会自动每天运行！** 🚀

