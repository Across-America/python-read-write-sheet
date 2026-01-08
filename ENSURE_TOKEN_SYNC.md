# 确保本地和GitHub Actions使用相同的Token

## ✅ 当前状态

根据验证结果：
- ✅ **本地Token**: 已配置且有效
- ✅ **GitHub Secrets**: 已存在且最近更新（2026-01-08）
- ✅ **Token有效性**: 所有token都通过了测试

## 🔄 同步流程

### 方法1: 自动同步（推荐）

使用同步脚本一键同步：

```bash
python scripts/sync_token_to_github_secrets.py
```

**功能**:
- 自动读取本地 `.env` 文件中的token
- 加密并更新到GitHub Secrets
- 显示详细的更新结果

### 方法2: 手动同步

1. **获取本地token**:
   ```bash
   # 查看本地token（前10个字符）
   python scripts/verify_token_sync.py
   ```

2. **更新GitHub Secrets**:
   - 访问: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions
   - 点击要更新的secret
   - 点击 "Update"
   - 粘贴本地 `.env` 文件中的完整token
   - 保存

## ✅ 验证同步状态

运行验证脚本检查：

```bash
python scripts/verify_token_sync.py
```

**验证内容**:
- ✅ 本地token是否存在
- ✅ GitHub Secrets是否存在
- ✅ 本地token是否有效
- ✅ 提供同步建议

## 📋 定期维护清单

### 每周检查

```bash
# 1. 验证token状态
python scripts/verify_token_sync.py

# 2. 如果本地token更新了，同步到GitHub
python scripts/sync_token_to_github_secrets.py
```

### 当本地token更新时

1. **更新本地 `.env` 文件**
2. **立即同步到GitHub**:
   ```bash
   python scripts/sync_token_to_github_secrets.py
   ```
3. **验证同步**:
   ```bash
   python scripts/verify_token_sync.py
   ```
4. **测试workflow**:
   - 访问GitHub Actions页面
   - 手动触发workflow
   - 检查日志确认token有效

## 🔍 故障排除

### 问题1: 本地可以但GitHub Actions失败

**原因**: GitHub Secrets中的token可能不同或已过期

**解决**:
```bash
# 同步本地token到GitHub
python scripts/sync_token_to_github_secrets.py
```

### 问题2: 验证脚本显示token无效

**检查**:
1. 确认 `.env` 文件中的token正确
2. 测试token是否真的有效：
   ```bash
   python scripts/diagnose_smartsheet_404.py
   ```

**解决**:
- 如果本地token无效，更新 `.env` 文件
- 然后同步到GitHub

### 问题3: GitHub Secrets不存在

**解决**:
```bash
# 运行同步脚本会自动创建
python scripts/sync_token_to_github_secrets.py
```

## 📝 最佳实践

### 1. 统一Token管理

- ✅ 使用相同的token（如果安全允许）
- ✅ 本地和GitHub使用相同的token值
- ✅ 定期同步确保一致性

### 2. 变更流程

当需要更新token时：

```
更新本地.env → 同步到GitHub → 验证 → 测试workflow
```

### 3. 文档记录

- 记录token的生成日期
- 记录token的用途
- 记录更新历史

## 🚀 快速命令参考

```bash
# 验证token同步状态
python scripts/verify_token_sync.py

# 同步本地token到GitHub
python scripts/sync_token_to_github_secrets.py

# 诊断Smartsheet访问问题
python scripts/diagnose_smartsheet_404.py

# 监控GitHub Actions状态
python scripts/monitor_github_actions.py
```

## ✅ 当前验证结果

根据最新验证（2026-01-08）:

- ✅ **SMARTSHEET_ACCESS_TOKEN**:
  - 本地: 已设置（37字符，X9JpGfnIuo...）
  - GitHub: 已存在（最后更新: 2026-01-08T18:21:20Z）
  - 有效性: ✅ 通过（可访问Sheet，2809行）

- ✅ **VAPI_API_KEY**:
  - 本地: 已设置（36字符，763666f4-1...）
  - GitHub: 已存在（最后更新: 2026-01-08T18:21:21Z）
  - 有效性: ✅ 通过（VAPI API可访问）

**结论**: 本地和GitHub Actions已同步，使用相同的token！

## 🔗 相关文档

- [本地运行 vs GitHub Actions](./LOCAL_VS_GITHUB_ACTIONS.md)
- [同步Token指南](./scripts/SYNC_TOKEN_GUIDE.md)
- [STM1 Smartsheet 404错误修复](./STM1_SMARTSHEET_404_FIX.md)
