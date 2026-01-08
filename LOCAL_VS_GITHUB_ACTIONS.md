# 本地运行 vs GitHub Actions - 关键区别

## 重要说明

**本地运行成功 ≠ GitHub Actions一定成功**

两者使用不同的环境变量和配置，需要分别设置。

## 主要区别

### 1. 环境变量来源不同

| 环境 | 环境变量来源 | 位置 |
|------|------------|------|
| **本地** | `.env` 文件 | 项目根目录的 `.env` 文件 |
| **GitHub Actions** | GitHub Secrets | https://github.com/.../settings/secrets/actions |

### 2. 当前问题分析

从您的日志来看：

**本地环境** ✅:
- 使用 `.env` 文件中的 `SMARTSHEET_ACCESS_TOKEN`
- Sheet可以正常访问（2809行）
- 所有功能正常

**GitHub Actions** ❌:
- 使用 GitHub Secrets 中的 `SMARTSHEET_ACCESS_TOKEN`
- 返回404错误
- **说明：GitHub Secrets中的token可能不同或已过期**

## 如何确保两者都成功

### 步骤1: 确认本地token

```bash
# 检查本地.env文件中的token
python scripts/diagnose_smartsheet_404.py
```

### 步骤2: 更新GitHub Secrets

1. **获取本地使用的token**:
   - 查看 `.env` 文件中的 `SMARTSHEET_ACCESS_TOKEN`
   - 或运行诊断脚本查看token的前10个字符

2. **更新GitHub Secret**:
   - 访问: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions
   - 找到 `SMARTSHEET_ACCESS_TOKEN`
   - 点击 "Update"
   - **使用与本地 `.env` 文件中相同的token**
   - 保存

3. **验证**:
   - 重新运行workflow
   - 检查日志确认是否修复

## 常见问题

### Q: 为什么本地可以但GitHub Actions不行？

**A:** 因为使用了不同的token：
- 本地：`.env` 文件中的token（有效）
- GitHub Actions：GitHub Secrets中的token（可能无效或过期）

### Q: 如何确保使用相同的token？

**A:** 
1. 复制 `.env` 文件中的 `SMARTSHEET_ACCESS_TOKEN`
2. 更新GitHub Secrets中的 `SMARTSHEET_ACCESS_TOKEN`
3. 确保两者完全一致

### Q: 本地测试通过后，GitHub Actions还需要做什么？

**A:**
1. ✅ 确保代码已提交到GitHub
2. ✅ 确保GitHub Secrets中的token与本地相同
3. ✅ 确保所有依赖都正确安装
4. ✅ 运行workflow测试

## 最佳实践

### 1. 统一Token管理

**推荐做法**:
- 使用相同的token（如果安全允许）
- 定期同步本地和GitHub Secrets中的token
- 记录token的生成日期和有效期

### 2. 测试流程

```
本地测试 → 提交代码 → 检查GitHub Secrets → 运行workflow → 验证结果
```

### 3. 验证清单

在提交代码前，确认：
- [ ] 本地测试通过
- [ ] GitHub Secrets已设置
- [ ] Token与本地相同
- [ ] 代码已提交
- [ ] Workflow可以手动触发测试

## 当前问题的解决方案

### 立即修复

1. **检查本地token**:
   ```bash
   python scripts/diagnose_smartsheet_404.py
   ```
   记录token的前10个字符

2. **更新GitHub Secret**:
   - 访问GitHub Secrets页面
   - 更新 `SMARTSHEET_ACCESS_TOKEN`
   - 使用与本地相同的token

3. **重新运行workflow**:
   - 手动触发一次测试
   - 查看日志确认修复

### 验证修复

修复后，运行：
```bash
# 检查workflow状态
python scripts/monitor_github_actions.py

# 查看最新运行日志
python scripts/check_workflow_logs.py
```

## 总结

- ✅ **本地成功是必要条件，但不是充分条件**
- ✅ **GitHub Actions需要单独配置环境变量（Secrets）**
- ✅ **确保两者使用相同的token才能保证一致性**
- ✅ **定期检查GitHub Secrets是否与本地同步**
