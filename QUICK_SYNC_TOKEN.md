# 快速同步Token到GitHub Secrets

## 一键同步本地Token到GitHub

### 步骤1: 安装依赖

```bash
pip install pynacl requests
```

### 步骤2: 确保GitHub Token已配置

在 `.env` 文件中添加（如果还没有）：
```
GITHUB_TOKEN=your_github_token_here
```

**注意**: 将 `your_github_token_here` 替换为您的实际GitHub Personal Access Token

### 步骤3: 运行同步脚本

```bash
python scripts/sync_token_to_github_secrets.py
```

## 脚本功能

✅ 自动读取本地 `.env` 文件中的token  
✅ 自动加密并更新到GitHub Secrets  
✅ 同步 `SMARTSHEET_ACCESS_TOKEN` 和 `VAPI_API_KEY`  
✅ 显示详细的更新结果  

## 验证

同步后：
1. 访问: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions
2. 确认secrets已更新
3. 重新运行workflow测试

## 详细文档

查看 `scripts/SYNC_TOKEN_GUIDE.md` 获取完整说明。
