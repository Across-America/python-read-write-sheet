# Twilio Setup Guide for VAPI Integration

## 🚨 问题
VAPI提供的电话号码有每日外呼限制，无法满足大量呼叫需求（几百个电话/天）。

## 💡 解决方案
使用你自己的Twilio电话号码，可以无限制外呼。

## 📋 设置步骤

### 1. 注册Twilio账号
1. 访问 [twilio.com](https://www.twilio.com)
2. 点击 "Sign up" 注册账号
3. 验证邮箱和手机号
4. 完成身份验证

### 2. 购买电话号码
1. 登录Twilio Console
2. 进入 "Phone Numbers" > "Manage" > "Buy a number"
3. 选择国家/地区（美国推荐）
4. 选择支持语音的号码
5. 购买号码（约$1/月）

### 3. 配置Twilio号码
1. 在Twilio Console中找到你的号码
2. 点击号码进入配置页面
3. 设置以下配置：
   - **Voice Configuration**: Webhook
   - **Webhook URL**: `https://api.vapi.ai/webhook/twilio`
   - **HTTP Method**: POST
   - **Save** 配置

### 4. 在VAPI中导入号码
1. 登录VAPI Dashboard
2. 进入 "Phone Numbers" 部分
3. 点击 "Import Twilio Number"
4. 输入你的Twilio账号信息：
   - Account SID
   - Auth Token
   - Phone Number SID
5. 完成导入

### 5. 更新代码配置
在 `auto_call_and_update.py` 中添加新的电话号码ID：

```python
PHONE_NUMBER_IDS = [
    "2f8d40fa-32c8-421b-8c70-ec877e4e9948",  # 原始VAPI号码
    "your_new_twilio_phone_id_1",             # 新的Twilio号码1
    "your_new_twilio_phone_id_2",             # 新的Twilio号码2
    # 可以添加更多号码
]
```

## 🔧 批量呼叫系统

使用新的批量呼叫系统：

```bash
python3 batch_call_system.py
```

### 功能特点：
- ✅ 自动轮换电话号码
- ✅ 速率限制（避免超过限制）
- ✅ 错误处理和重试
- ✅ 进度跟踪
- ✅ 结果统计

### 配置参数：
- `delay_between_calls`: 呼叫间隔（默认30秒）
- `max_calls_per_hour`: 每小时最大呼叫数（默认50个）

## 📊 成本估算

### Twilio成本：
- 电话号码：$1/月
- 语音通话：$0.013/分钟
- 假设每次通话2分钟，100个电话 = $2.6

### VAPI成本：
- 按使用量计费
- 通常比Twilio便宜

## 🚀 推荐配置

### 小规模（<100个电话/天）：
- 使用1个Twilio号码
- 30秒间隔
- 每小时最多20个电话

### 中规模（100-500个电话/天）：
- 使用2-3个Twilio号码
- 20秒间隔
- 每小时最多30个电话

### 大规模（>500个电话/天）：
- 使用5-10个Twilio号码
- 15秒间隔
- 每小时最多50个电话

## ⚠️ 注意事项

1. **合规性**：确保遵守当地法律法规
2. **时间限制**：避免在非营业时间呼叫
3. **频率限制**：不要过于频繁呼叫同一客户
4. **监控**：定期检查呼叫质量和成功率

## 🔍 故障排除

### 常见问题：
1. **号码无法导入**：检查Twilio配置和权限
2. **呼叫失败**：检查网络连接和API密钥
3. **限制错误**：增加延迟时间或使用更多号码

### 联系支持：
- Twilio支持：support@twilio.com
- VAPI支持：通过dashboard联系

## 📈 监控和优化

1. **成功率监控**：定期检查呼叫成功率
2. **成本优化**：监控使用量和成本
3. **性能调优**：根据结果调整参数

---

**下一步**：按照上述步骤设置Twilio，然后运行批量呼叫系统测试。
