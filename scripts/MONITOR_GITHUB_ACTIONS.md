# 如何监控GitHub Actions Workflow运行情况

## 方法1: 直接访问GitHub Actions页面（最简单）

### 访问链接
https://github.com/Across-America/python-read-write-sheet/actions/workflows/daily-stm1.yml

### 查看内容
- ✅ 最近的运行记录
- ✅ 运行状态（成功/失败/进行中）
- ✅ 运行时间
- ✅ 详细日志

### 状态图标说明
- ✅ 绿色 ✓ = 成功
- ❌ 红色 ✗ = 失败
- 🟡 黄色 ⚠ = 进行中
- ⚪ 灰色 ⚪ = 未运行

## 方法2: 使用监控脚本（推荐）

### 运行监控脚本
```bash
python scripts/monitor_github_actions.py
```

### 功能
- 📊 显示最近5次运行记录
- 📈 统计成功/失败次数
- ⏰ 显示运行时间和持续时间
- 🔗 提供直接访问日志的链接
- 📋 显示每个job的详细状态

### 配置要求
需要设置 `GITHUB_TOKEN` 环境变量：

1. **获取GitHub Token**:
   - 访问: https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 选择权限: `repo` (全部权限)
   - 生成并复制token

2. **设置环境变量**:
   ```bash
   # Windows PowerShell
   $env:GITHUB_TOKEN="your_token_here"
   
   # Windows CMD
   set GITHUB_TOKEN=your_token_here
   
   # Linux/Mac
   export GITHUB_TOKEN=your_token_here
   ```

3. **或在.env文件中添加**:
   ```
   GITHUB_TOKEN=your_token_here
   ```

## 方法3: 使用GitHub API（高级）

### API端点
```
GET https://api.github.com/repos/Across-America/python-read-write-sheet/actions/workflows/daily-stm1.yml/runs
```

### 需要认证
在请求头中添加:
```
Authorization: token YOUR_GITHUB_TOKEN
```

### 示例响应
```json
{
  "workflow_runs": [
    {
      "id": 123456789,
      "status": "completed",
      "conclusion": "success",
      "created_at": "2026-01-08T17:00:00Z",
      "updated_at": "2026-01-08T17:30:00Z",
      "html_url": "https://github.com/.../actions/runs/123456789"
    }
  ]
}
```

## 方法4: 设置通知（自动监控）

### GitHub通知设置
1. 访问: https://github.com/settings/notifications
2. 启用 "Actions" 通知
3. 选择通知方式:
   - Email
   - Web
   - Mobile

### 通知触发条件
- ✅ Workflow运行成功
- ❌ Workflow运行失败
- 🔄 Workflow运行超时

## 方法5: 使用GitHub Actions Status Badge

### 在README中添加badge
```markdown
![STM1 Workflow](https://github.com/Across-America/python-read-write-sheet/actions/workflows/daily-stm1.yml/badge.svg)
```

### 实时显示状态
- 绿色 = 最近一次运行成功
- 红色 = 最近一次运行失败
- 黄色 = 最近一次运行进行中

## 监控检查清单

### 每日检查
- [ ] 检查workflow是否按时运行（UTC 16:00或17:00）
- [ ] 检查运行状态（成功/失败）
- [ ] 检查是否有错误日志
- [ ] 检查是否开始拨打电话（查看日志中的"Call #1"）

### 每周检查
- [ ] 统计成功/失败率
- [ ] 检查是否有重复失败
- [ ] 检查运行时间是否正常
- [ ] 检查是否有性能问题

## 常见问题排查

### Q: 如何查看运行日志？
**A:** 
1. 访问workflow页面
2. 点击失败的运行记录
3. 点击 "Run Automated STM1 Calling" job
4. 查看详细日志

### Q: 如何知道workflow是否正在运行？
**A:**
1. 查看workflow页面，状态显示为 "in_progress"
2. 运行监控脚本，查看状态
3. 查看运行时间，如果刚创建且未完成，说明正在运行

### Q: 如何设置失败通知？
**A:**
1. 在GitHub设置中启用Actions通知
2. 或使用GitHub API创建webhook
3. 或使用第三方监控服务（如Uptime Robot）

### Q: 如何查看历史运行记录？
**A:**
1. 访问workflow页面，查看"All workflows"列表
2. 使用监控脚本，增加`per_page`参数
3. 使用GitHub API，添加分页参数

## 快速检查命令

```bash
# 运行监控脚本
python scripts/monitor_github_actions.py

# 检查workflow状态（需要curl和jq）
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/Across-America/python-read-write-sheet/actions/workflows/daily-stm1.yml/runs \
  | jq '.workflow_runs[0] | {status, conclusion, created_at}'
```

## 最佳实践

1. **定期检查**: 每天至少检查一次workflow运行状态
2. **设置通知**: 启用失败通知，及时发现问题
3. **查看日志**: 即使运行成功，也要定期查看日志确认功能正常
4. **记录问题**: 如果发现问题，记录在issue或文档中
5. **监控趋势**: 关注成功率和运行时间趋势，及早发现问题
