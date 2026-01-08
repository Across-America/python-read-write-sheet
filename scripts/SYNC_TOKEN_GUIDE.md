# 自动同步Token到GitHub Secrets指南

## 功能说明

`sync_token_to_github_secrets.py` 脚本可以自动将本地 `.env` 文件中的token同步到GitHub Secrets，确保本地和GitHub Actions使用相同的token。

## 前置要求

### 1. 安装依赖

```bash
pip install pynacl requests
```

或者安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 配置GitHub Token

需要GitHub Personal Access Token (PAT) 来访问GitHub API。

**获取PAT**:
1. 访问: https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择权限：
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
4. 生成并复制token

**设置PAT**:
- 方法1: 添加到 `.env` 文件
  ```
  GITHUB_TOKEN=ghp_your_token_here
  ```
- 方法2: 设置环境变量
  ```powershell
  # Windows PowerShell
  $env:GITHUB_TOKEN='ghp_your_token_here'
  ```

## 使用方法

### 基本使用

```bash
python scripts/sync_token_to_github_secrets.py
```

### 同步的Token

脚本会自动同步以下token（如果在 `.env` 文件中存在）：
- `SMARTSHEET_ACCESS_TOKEN`
- `VAPI_API_KEY`

## 工作流程

1. **读取本地token**: 从 `.env` 文件读取 `SMARTSHEET_ACCESS_TOKEN` 和 `VAPI_API_KEY`
2. **获取GitHub Public Key**: 从GitHub API获取仓库的public key用于加密
3. **加密token**: 使用public key加密每个token值
4. **更新GitHub Secrets**: 通过GitHub API更新对应的secret
5. **验证结果**: 显示更新成功或失败的信息

## 示例输出

```
================================================================================
Sync Local Tokens to GitHub Secrets
================================================================================

[OK] GitHub token found (starts with: ghp_YyWUL...)

Local tokens found:
   SMARTSHEET_ACCESS_TOKEN: 37 characters (starts with: X9JpGfnIuo...)
   VAPI_API_KEY: 45 characters (starts with: abc123def4...)

Repository: Across-America/python-read-write-sheet

Step 1: Getting repository public key...
[OK] Public key retrieved (key_id: abc123...)

Step 2: Updating SMARTSHEET_ACCESS_TOKEN...
[OK] SMARTSHEET_ACCESS_TOKEN updated successfully

Step 2: Updating VAPI_API_KEY...
[OK] VAPI_API_KEY updated successfully

================================================================================
Summary
================================================================================
   Successfully updated: 2 secret(s)
   All secrets updated successfully!

[INFO] Secrets have been updated in GitHub
   Next steps:
   1. Go to: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions
   2. Verify the secrets are updated
   3. Re-run the workflow to test
```

## 常见问题

### Q: 为什么需要GitHub Token？

**A:** GitHub API需要认证才能更新Secrets。PAT用于：
- 获取仓库的public key
- 更新GitHub Secrets

### Q: 更新后需要做什么？

**A:**
1. 验证GitHub Secrets已更新
2. 重新运行workflow测试
3. 检查workflow日志确认token有效

### Q: 如果更新失败怎么办？

**A:** 检查：
1. GitHub Token是否有正确的权限（`repo` scope）
2. GitHub Token是否有效
3. 仓库名称是否正确
4. 网络连接是否正常

### Q: 可以只更新一个token吗？

**A:** 可以。脚本只会同步 `.env` 文件中存在的token。如果只想更新 `SMARTSHEET_ACCESS_TOKEN`，确保 `.env` 文件中只有这个token。

### Q: 更新后本地和GitHub Actions会使用相同的token吗？

**A:** 是的！这就是同步的目的。确保：
- 本地 `.env` 文件中的token有效
- 同步后，GitHub Actions会使用相同的token

## 安全提示

⚠️ **重要**:
- GitHub Token (PAT) 是敏感信息，不要提交到代码仓库
- 确保 `.env` 文件在 `.gitignore` 中
- 定期轮换token以提高安全性
- 不要分享PAT给他人

## 验证同步结果

### 方法1: 检查GitHub Secrets页面

访问: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions

确认secrets已更新（注意：GitHub不会显示secret的值，只能看到名称和最后更新时间）。

### 方法2: 运行workflow测试

1. 访问: https://github.com/Across-America/python-read-write-sheet/actions
2. 选择 "Daily STM1 Automated Calling" workflow
3. 点击 "Run workflow"
4. 检查日志确认是否成功

### 方法3: 使用监控脚本

```bash
python scripts/monitor_github_actions.py
```

查看最新的workflow运行状态。

## 最佳实践

1. **定期同步**: 当本地token更新时，立即同步到GitHub
2. **测试验证**: 同步后运行workflow测试确认
3. **记录变更**: 记录token更新的日期和原因
4. **备份token**: 在安全的地方备份token（如密码管理器）

## 故障排除

### 错误: "PyNaCl library is required"

**解决**: 安装依赖
```bash
pip install pynacl
```

### 错误: "GITHUB_TOKEN not found"

**解决**: 设置GitHub Token
- 添加到 `.env` 文件: `GITHUB_TOKEN=ghp_...`
- 或设置环境变量

### 错误: "Failed to get public key" (401 Unauthorized)

**解决**: 
- 检查GitHub Token是否有效
- 确认Token有 `repo` 权限

### 错误: "Failed to update secret" (403 Forbidden)

**解决**:
- 确认Token有 `repo` 和 `workflow` 权限
- 确认有仓库的管理权限

## 相关文档

- [本地运行 vs GitHub Actions](./LOCAL_VS_GITHUB_ACTIONS.md)
- [STM1 Smartsheet 404错误修复指南](../STM1_SMARTSHEET_404_FIX.md)
- [监控GitHub Actions](./MONITOR_GITHUB_ACTIONS.md)
