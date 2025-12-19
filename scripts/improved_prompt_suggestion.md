# Prompt改进建议

## ✅ 当前Prompt的优点
- ✅ 明确说明"Do NOT call STM_end_call_tool" after transfer
- ✅ 清晰区分TRANSFER和END CALL场景
- ✅ 使用正确的工具名称

## 💡 建议的小改进

在Step 2的YES部分，添加一行说明transfer会自动结束电话：

**当前：**
```
**If customer says YES, okay, sure, yeah, or any positive response:**
→ Say: "Great, I will transfer you now. Please hold."
→ Use **transfer_call_to_AllClaim** tool to transfer
→ Do NOT call STM_end_call_tool
```

**建议改为：**
```
**If customer says YES, okay, sure, yeah, or any positive response:**
→ Say: "Great, I will transfer you now. Please hold."
→ IMMEDIATELY call **transfer_call_to_AllClaim** tool to transfer
→ CRITICAL: After calling transfer_call_to_AllClaim, DO NOT call STM_end_call_tool
→ The call will automatically end when transfer completes - you do NOT need to end it manually
→ STOP speaking after calling transfer_call_to_AllClaim - let the transfer happen
```

## 🧪 测试建议

当前prompt已经足够好了，可以直接测试。如果测试后仍然有问题，再添加上述改进。


