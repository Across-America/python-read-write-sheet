# 批量呼叫测试脚本使用指南

## 脚本功能
`test_batch_call_not_called.py` 是一个专门用于批量呼叫的测试脚本，它会：

1. 搜索 Smartsheet 中 `Call Status` 为 "Not call yet" 的所有客户
2. 使用 VAPI 的 Spencer: Call Transfer V2 Campaign 助手
3. 使用公司号码 +1 (951) 247-2003 作为来电显示
4. 批量呼叫所有符合条件的客户
5. 自动更新 Smartsheet 中的呼叫状态

## 使用方法

### 1. 运行脚本
```bash
cd /Users/rickyang/Desktop/AIOutboundCall/python-read-write-sheet
python test_batch_call_not_called.py
```

### 2. 选择测试模式
脚本会显示三个选项：

- **选项 1**: 测试单个客户呼叫（推荐先测试）
- **选项 2**: 批量呼叫所有 "Not call yet" 客户
- **选项 3**: 仅显示客户列表（不进行呼叫）

### 3. 推荐测试流程

#### 第一步：查看客户列表
```bash
python test_batch_call_not_called.py
# 选择选项 3
```

#### 第二步：测试单个客户
```bash
python test_batch_call_not_called.py
# 选择选项 1
```

#### 第三步：批量呼叫（确认无误后）
```bash
python test_batch_call_not_called.py
# 选择选项 2
```

## 脚本特性

### 🔍 智能搜索
- 自动搜索 `Call Status` 为 "Not call yet" 的客户
- 验证电话号码有效性（至少10位数字）
- 排除 "No phone number" 的记录

### 📞 批量呼叫
- 使用 VAPI 官方批量呼叫 API
- 支持 `customers` 参数传递多个客户
- 每个客户都有个性化的上下文信息

### 🏢 公司号码
- 硬性要求使用公司号码 +1 (951) 247-2003
- 客户看到的是公司官方号码

### 📝 状态更新
- 呼叫前：更新状态为 "Calling"
- 呼叫成功：更新状态为 "Called"
- 呼叫失败：恢复状态为 "Not call yet"

## 客户信息传递

脚本会为每个客户传递以下信息给 VAPI 助手：

```json
{
  "customer_name": "客户姓名",
  "policy_number": "保单号",
  "agent_name": "代理人姓名",
  "office": "办公室",
  "lob": "保险类型",
  "status": "状态",
  "cancellation_reason": "取消原因",
  "cancellation_date": "取消日期",
  "client_id": "客户ID"
}
```

## 安全特性

### ⚠️ 确认机制
- 批量呼叫前会显示客户数量和详细信息
- 需要用户确认才会进行实际呼叫
- 显示费用警告

### 🔄 错误处理
- 呼叫失败时自动恢复状态
- 详细的错误日志记录
- 支持重试机制

### 📊 进度跟踪
- 实时显示呼叫进度
- 详细的成功/失败统计
- 结果保存到文件

## 注意事项

1. **费用警告**: 每次呼叫都会产生费用
2. **测试建议**: 建议先测试单个客户再批量呼叫
3. **状态管理**: 脚本会自动管理 Smartsheet 中的状态
4. **错误恢复**: 如果呼叫失败，状态会自动恢复

## 故障排除

### 常见问题

1. **没有找到客户**
   - 检查 Smartsheet 中是否有 "Not call yet" 状态的记录
   - 确认电话号码列有有效数据

2. **呼叫失败**
   - 检查 VAPI API 密钥是否有效
   - 确认网络连接正常
   - 查看错误日志

3. **状态更新失败**
   - 检查 Smartsheet 访问权限
   - 确认 "Call Status" 列存在

### 日志文件
脚本运行时会显示详细的日志信息，包括：
- 客户搜索结果
- 呼叫状态更新
- API 响应信息
- 错误详情

## 技术支持

如果遇到问题，请检查：
1. 环境变量配置（VAPI_API_KEY, SMARTSHEET_ACCESS_TOKEN）
2. 网络连接
3. Smartsheet 权限
4. VAPI 账户状态
