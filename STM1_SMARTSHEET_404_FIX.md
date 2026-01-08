# STM1 GitHub Actions Smartsheet 404错误修复指南

## 问题描述

GitHub Actions workflow运行时，Smartsheet API返回404错误：
```
{"result": {"code": 1006, "errorCode": 1006, "message": "Not Found", ...}}
```

导致脚本无法加载客户列表，最终退出。

## 问题原因

**最可能的原因**: GitHub Actions中的`SMARTSHEET_ACCESS_TOKEN` secret没有正确设置或已过期。

## 诊断步骤

### 1. 检查GitHub Secrets

访问: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions

确认以下secrets存在且正确：
- ✅ `SMARTSHEET_ACCESS_TOKEN` - 必须存在
- ✅ `VAPI_API_KEY` - 必须存在

### 2. 验证Token有效性

**本地测试**:
```bash
python scripts/diagnose_smartsheet_404.py
```

**如果本地测试成功但GitHub Actions失败**:
- 说明GitHub Actions中的token可能不同或已过期
- 需要更新GitHub Secrets中的token

### 3. 检查Sheet ID

确认Sheet ID是否正确：
- 当前配置: `7093255935053700`
- Sheet名称: "Insured Driver Statement"
- Workspace: "AACS"

## 解决方案

### 方案1: 更新GitHub Secrets（推荐）

1. **获取新的Smartsheet Token**:
   - 访问: https://app.smartsheet.com/account
   - 生成新的API token
   - 确保token有访问"Insured Driver Statement" sheet的权限

2. **更新GitHub Secret**:
   - 访问: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions
   - 点击 `SMARTSHEET_ACCESS_TOKEN`
   - 点击 "Update"
   - 粘贴新的token
   - 保存

3. **重新运行workflow**:
   - 访问: https://github.com/Across-America/python-read-write-sheet/actions/workflows/daily-stm1.yml
   - 点击 "Run workflow"
   - 选择分支并运行

### 方案2: 检查Token权限

确保token有权限访问：
- AACS workspace
- Insured Driver Statement sheet

### 方案3: 使用Sheet名称查找（备用方案）

如果Sheet ID有问题，可以修改代码使用Sheet名称查找：

```python
# 在 workflows/stm1.py 的 get_stm1_sheet() 函数中
# 优先使用Sheet名称查找，而不是直接使用Sheet ID
smartsheet_service = SmartsheetService(
    sheet_name=STM1_SHEET_NAME,
    workspace_name=STM1_WORKSPACE_NAME
)
```

## 验证修复

修复后，运行以下命令验证：

```bash
# 本地测试
python scripts/diagnose_smartsheet_404.py

# 检查workflow状态
python scripts/monitor_github_actions.py
```

## 常见问题

### Q: 为什么本地可以访问但GitHub Actions不行？
**A:** 
- 本地使用的是`.env`文件中的token
- GitHub Actions使用的是GitHub Secrets中的token
- 两个token可能不同或GitHub Secrets中的token已过期

### Q: 如何确认GitHub Secrets中的token是否正确？
**A:**
1. 查看workflow日志中的错误信息
2. 如果看到404错误，说明token可能无效或没有权限
3. 更新token后重新运行workflow

### Q: Sheet ID会改变吗？
**A:**
- 通常不会，除非sheet被删除后重新创建
- 如果怀疑ID错误，可以使用Sheet名称查找

## 快速修复步骤

1. ✅ 访问GitHub Secrets页面
2. ✅ 检查`SMARTSHEET_ACCESS_TOKEN`是否存在
3. ✅ 如果不存在或不确定，生成新token并更新
4. ✅ 重新运行workflow
5. ✅ 检查日志确认是否修复

## 预防措施

1. **定期检查token有效性**: 每月检查一次
2. **使用环境变量**: 确保本地和GitHub Actions使用相同的token（如果可能）
3. **监控错误**: 设置通知，及时发现问题
4. **文档记录**: 记录token的生成日期和有效期
