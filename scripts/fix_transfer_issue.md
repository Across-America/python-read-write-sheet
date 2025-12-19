# 修复Transfer挂断问题

## 🔴 发现的问题

### 问题1：Transfer工具缺少phoneNumberId配置
- Transfer工具ID: `1a00db81-a056-4b43-a225-ba4fc387c812`
- **❌ Transfer Phone Number ID: Not set**
- **❌ Transfer Message: Not set**

**这是主要问题！** 没有配置转接目标号码，transfer会失败，然后assistant可能调用endCall。

### 问题2：Prompt中的工具名称不匹配
- Prompt提到: `transfer_call_to_AllClaim`, `STM_end_call_tool`
- 实际工具类型: `transferCall`, `endCall`

## ✅ 修复步骤

### 步骤1：配置Transfer工具的phoneNumberId（最重要！）

1. 登录VAPI Dashboard
2. 找到Tool ID: `1a00db81-a056-4b43-a225-ba4fc387c812`
3. 编辑这个transferCall工具
4. 设置 **Transfer Phone Number ID**（转接目标号码的ID）
5. 可选：设置 **Transfer Message**（如："Please hold while I transfer you"）

### 步骤2：修改Prompt使用正确的工具名称

将prompt中的工具名称改为实际工具类型：

**修改前：**
```
→ Use **transfer_call_to_AllClaim** tool to transfer
→ Call **STM_end_call_tool** to end the call
```

**修改后：**
```
→ Use **transferCall** tool to transfer
→ Use **endCall** tool to end the call
```

### 步骤3：更严格的Prompt修改（防止transfer后调用endCall）

**修改Step 3部分：**

```
### Step 3: Transfer to Live Agent
**If customer says YES, okay, sure, yeah, or any positive response:**
→ Say: "Great, I will transfer you now. Please hold."
→ IMMEDIATELY call **transferCall** tool (DO NOT skip this step!)
→ CRITICAL: After calling transferCall tool, DO NOT call endCall tool
→ The call will automatically end when transfer completes
→ You MUST NOT manually end the call after transfer
→ STOP speaking after calling transferCall - let the transfer happen
```

**修改CRITICAL RULES部分：**

```
## CRITICAL RULES

1. **When customer says YES:**
   - Call transferCall tool
   - DO NOT call endCall tool after transferCall
   - The call ends automatically after transfer

2. **When customer says NO:**
   - Thank them politely
   - Call endCall tool to end the call

3. **NEVER call endCall after calling transferCall**
   - Transfer tool automatically handles call ending
   - Calling endCall after transfer will disconnect the customer
```

## 📋 完整的修改后的Prompt关键部分

```
## Call Flow

**If customer says YES, okay, sure, yeah, or any positive response:**
→ Say: "Great, I will transfer you now. Please hold."
→ IMMEDIATELY call **transferCall** tool
→ DO NOT call **endCall** tool after transferCall
→ The call will automatically end when transfer completes
→ STOP speaking after calling transferCall

**If customer says NO, not now, busy, or any negative response:**
→ Say: "No problem. We will call you back another time. Thank you. Goodbye."
→ Call **endCall** tool to end the call

**If customer asks questions or is unsure:**
→ Briefly explain and re-ask if they have time now
→ If still no: Say "Thank you. Goodbye." → Call **endCall** tool

## CRITICAL RULES

1. **Transfer Rule:** When you call transferCall tool, DO NOT call endCall tool
2. **End Call Rule:** Only call endCall when customer says NO or is not available
3. **Never call endCall after transferCall** - transfer handles call ending automatically
```

## 🧪 测试步骤

1. 配置transfer工具的phoneNumberId
2. 修改prompt使用正确的工具名称（transferCall, endCall）
3. 添加明确的"不要transfer后调用endCall"的指令
4. 测试第120行
5. 确认客户真的被转接，而不是被挂断


