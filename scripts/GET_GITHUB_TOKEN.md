# 🔑 如何获取 GitHub Token

## 📋 详细步骤

### 步骤 1: 访问 Token 设置页面

1. 打开浏览器，访问：
   ```
   https://github.com/settings/tokens
   ```
   
   或者：
   - 登录 GitHub
   - 点击右上角头像
   - 选择 **Settings**
   - 左侧菜单找到 **Developer settings**
   - 点击 **Personal access tokens**
   - 选择 **Tokens (classic)**

### 步骤 2: 生成新 Token

1. 点击 **"Generate new token"** 按钮
2. 选择 **"Generate new token (classic)"**（经典版本）

### 步骤 3: 配置 Token

1. **Note（备注）**: 输入一个描述性名称，例如：
   ```
   Workflow Status Checker
   ```

2. **Expiration（过期时间）**: 选择过期时间
   - 建议选择 **"No expiration"**（永不过期）或 **"90 days"**（90天）

3. **Select scopes（选择权限）**: 
   - ✅ 勾选 **`repo`** 
     - 这会自动勾选所有子权限：
       - ✅ repo:status
       - ✅ repo_deployment
       - ✅ public_repo
       - ✅ repo:invite
       - ✅ security_events

### 步骤 4: 生成并复制 Token

1. 滚动到页面底部
2. 点击 **"Generate token"** 按钮
3. **⚠️ 重要**: Token 只会显示一次！
4. **立即复制** token（一串很长的字符串，类似：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）
5. **保存好** token，不要分享给他人

---

## 🚀 使用 Token

### 方式 1: 环境变量（推荐）

**PowerShell:**
```powershell
$env:GITHUB_TOKEN="ghp_你的token"
python scripts/check_github_actions_status.py
```

**命令提示符 (CMD):**
```cmd
set GITHUB_TOKEN=ghp_你的token
python scripts/check_github_actions_status.py
```

### 方式 2: 命令行参数

```powershell
python scripts/check_github_actions_status.py --token ghp_你的token
```

### 方式 3: 临时设置（当前会话）

**PowerShell:**
```powershell
# 设置环境变量（仅当前 PowerShell 窗口有效）
$env:GITHUB_TOKEN="ghp_你的token"

# 运行脚本
python scripts/check_github_actions_status.py
```

---

## 🔒 安全提示

1. **不要提交 token 到 Git**
   - Token 已经在 `.gitignore` 中，不会被提交
   - 不要将 token 写入代码文件

2. **不要分享 token**
   - Token 等同于你的密码
   - 如果泄露，立即撤销并重新生成

3. **定期检查 token**
   - 访问 https://github.com/settings/tokens
   - 查看已生成的 token
   - 如果不再使用，可以撤销（Revoke）

---

## ❓ 常见问题

### Q: Token 过期了怎么办？

A: 重新生成一个新 token，步骤同上。

### Q: 忘记保存 token 了？

A: Token 只显示一次，如果忘记保存，需要重新生成。

### Q: Token 权限不够？

A: 确保勾选了 `repo` 权限，这包含了查看 Actions 所需的所有权限。

### Q: 如何撤销 token？

A: 
1. 访问 https://github.com/settings/tokens
2. 找到对应的 token
3. 点击 **"Revoke"** 按钮

---

## ✅ 验证 Token 是否有效

运行以下命令测试：

```powershell
# 设置 token
$env:GITHUB_TOKEN="ghp_你的token"

# 测试查询（会显示帮助信息）
python scripts/check_github_actions_status.py
```

如果 token 有效，脚本会开始查询。如果无效，会显示错误信息。

