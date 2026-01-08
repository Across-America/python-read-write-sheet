# 如何检查GitHub Actions日志来诊断STM1问题

## 访问日志

1. **访问workflow页面**:
   https://github.com/Across-America/python-read-write-sheet/actions/workflows/daily-stm1.yml

2. **查看最近的运行**:
   - 点击最近的运行记录
   - 点击 "Run Automated STM1 Calling" 步骤
   - 查看完整日志

## 关键日志信息

### ✅ 正常情况应该看到的日志

1. **脚本启动**:
   ```
   ================================================================================
   🤖 AUTOMATED STM1 CALLING - EMPTY CALLED_TIMES
   ================================================================================
   ⏰ Running from 9:00 AM to 4:55 PM Pacific Time
   ⏱️  Delay between calls: 36 seconds
   ```

2. **时间检查**:
   ```
   ⏰ Current time: 09:00 AM PST
   ✅ 当前在调用时间内
   ```

3. **服务初始化**:
   ```
   ================================================================================
   🔧 INITIALIZING SERVICES
   ================================================================================
   ✅ Services initialized
   🤖 Assistant ID: e9ec024e-5b90-4da2-8550-07917463978f
   📱 Phone Number ID: 5b2df9f4-780d-4ef6-9e01-0e55b1ba5d82
   ```

4. **加载客户**:
   ```
   [09:00:00] Loading customers with empty called_times...
   [09:00:01] Found 2150 customers to call
   ```

5. **开始拨打电话**:
   ```
   ================================================================================
   📞 Call #1: Row 202 - Maverick Express Carriers LLC
   Phone: 552-752-9867
   Time: 09:00:05 AM PST
   ================================================================================
   🚀 Initiating call...
   ✅ Call initiated (ID: ...)
   ```

### ❌ 问题情况

#### 问题1: 时间太早
如果看到:
```
⏰ Current time: 08:00 AM PST
⏰ Too early - GitHub Actions detected. Current time is before 9:00 AM Pacific Time
   Workflow should be scheduled for UTC 16:00 (PDT) or UTC 17:00 (PST) to match 9:00 AM Pacific Time
   Exiting. Will try again at the next scheduled run.
```
**原因**: GitHub Actions运行时间不对，Pacific时间还没到9 AM
**解决**: 检查workflow的schedule时间是否正确

#### 问题2: 没有客户
如果看到:
```
[09:00:00] Loading customers with empty called_times...
[09:00:01] Found 0 customers to call
✅ No more customers with empty called_times
   Waiting 5 minutes before checking again... (1/3)
```
然后重复3次后退出:
```
   No customers found after 3 attempts. Exiting.
```
**原因**: 所有客户的called_times都已>0
**解决**: 检查Smartsheet数据，确认是否有called_times=0的客户

#### 问题3: 加载客户失败
如果看到:
```
❌ Error loading customers: [错误信息]
   Retrying in 60 seconds...
```
**原因**: Smartsheet API调用失败
**解决**: 检查SMARTSHEET_ACCESS_TOKEN是否正确设置

#### 问题4: VAPI调用失败
如果看到:
```
🚀 Initiating call...
❌ Call failed - no results returned
```
或
```
❌ Exception during call: [错误信息]
```
**原因**: VAPI API调用失败
**解决**: 检查VAPI_API_KEY是否正确设置

#### 问题5: 时间检查导致退出
如果看到:
```
⏰ STOPPING AT 4:55 PM
   Current time: 04:55 PM PST
   Calls must stop by 4:55 PM Pacific Time (before 5 PM)
```
**原因**: 到达结束时间
**解决**: 这是正常的，脚本会在4:55 PM停止

## 常见问题排查

### Q: 日志显示脚本启动了，但没有看到"Call #1"的日志
**可能原因**:
1. 时间检查失败 - 检查是否有"Too early"或"Outside calling hours"的日志
2. 客户列表为空 - 检查是否有"No customers found"的日志
3. 循环中的时间检查 - 检查是否有"STOPPING AT 4:55 PM"的日志（如果时间不对）

### Q: 日志显示"Found 2150 customers"但没有拨打电话
**可能原因**:
1. 循环中的时间检查导致立即退出
2. 客户验证失败 - 检查是否有"Validation failed"的日志
3. VAPI调用异常 - 检查是否有异常堆栈信息

### Q: 如何确认脚本是否真的在运行？
**检查点**:
1. 查看是否有"Loop #10"、"Loop #20"等进度日志
2. 查看是否有"Still running..."的日志
3. 查看是否有任何错误或异常信息

## 建议的检查步骤

1. **首先检查时间**:
   - 确认workflow运行时间对应的Pacific时间
   - UTC 16:00 = 9:00 AM PDT (夏令时) 或 8:00 AM PST (标准时间)
   - UTC 17:00 = 10:00 AM PDT (夏令时) 或 9:00 AM PST (标准时间)

2. **检查客户列表**:
   - 确认日志中显示的客户数量
   - 如果为0，检查Smartsheet数据

3. **检查VAPI调用**:
   - 确认是否有"Call initiated"的日志
   - 如果没有，检查VAPI API配置

4. **检查异常**:
   - 查看完整的错误堆栈信息
   - 确认是否有未捕获的异常

## 快速诊断命令

如果需要本地测试，可以运行:
```bash
python scripts/diagnose_stm1_no_calls.py
```

这会检查所有可能的问题并给出诊断报告。
