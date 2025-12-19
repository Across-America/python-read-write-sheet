# Prompt修复建议 - Transfer后立即挂断问题

## 问题描述
客户回答"yes"后，assistant调用了transfer工具，但立即又调用了endCall工具，导致电话被挂断而不是转接。

## 当前Step 3的指令（有问题）：
```
### Step 3: Transfer to Live Agent
Say: "Great, I will now transfer you to one of our agents who will record your statement. Please hold for just a moment."
→ Use **transfer_call_to_AllClaim** tool to execute transfer
→ After transfer completes, immediately call **STM_end_call_tool**
```

## 问题分析
1. "After transfer completes"这个指令太模糊
2. Assistant可能在调用transfer工具后，立即认为transfer完成了
3. 实际上transfer可能还在进行中，或者需要等待
4. Assistant不应该在transfer后立即调用endCall

## 修复建议

### 方案1：明确说明不要立即调用endCall（推荐）

将Step 3改为：
```
### Step 3: Transfer to Live Agent
**If YES (available now):**
→ Say: "Great, I will now transfer you to one of our agents who will record your statement. Please hold for just a moment."
→ IMMEDIATELY call **transfer_call_to_AllClaim** tool (DO NOT skip this step!)
→ DO NOT call **STM_end_call_tool** after transfer - the call will end automatically when transfer completes
→ After calling transfer tool, STOP speaking and let the transfer happen
```

### 方案2：更明确的指令

```
### Step 3: Transfer to Live Agent
**If YES (available now):**
→ Say: "Great, I will now transfer you to one of our agents who will record your statement. Please hold for just a moment."
→ IMMEDIATELY call **transfer_call_to_AllClaim** tool
→ CRITICAL: After calling transfer tool, DO NOT call endCall tool
→ The call will automatically end when the transfer is complete
→ You do NOT need to manually end the call after transfer
```

### 方案3：完全移除transfer后的endCall指令

修改"CRITICAL: Call Ending Requirements"部分：
```
## CRITICAL: Call Ending Requirements
You MUST use the **STM_end_call_tool** to end the call in ALL of the following situations:
- Customer not available: thank them, then immediately call **STM_end_call_tool**
- After leaving voicemail: immediately call **STM_end_call_tool**
- Wrong number: apologize, then immediately call **STM_end_call_tool**
- After saying goodbye (when NOT transferring): immediately call **STM_end_call_tool**

**IMPORTANT:**
- Do NOT call **STM_end_call_tool** after calling transfer tool
- When you call transfer tool, the call will automatically end after transfer completes
- Only call **STM_end_call_tool** when the customer is NOT being transferred
```

## 关键修改点

1. **明确说明transfer后不要调用endCall**
2. **强调transfer工具调用后，电话会自动结束**
3. **只在非transfer场景下才调用endCall**

## 如何应用修复

1. 登录VAPI Dashboard
2. 找到STM1 Assistant (ID: e9ec024e-5b90-4da2-8550-07917463978f)
3. 编辑System Message/Prompt
4. 找到Step 3部分
5. 按照上述建议修改
6. 保存并测试

## 测试建议

修改后，测试以下场景：
1. 客户回答"yes" - 应该转接，不应该挂断
2. 客户回答"no" - 应该礼貌结束，调用endCall
3. 客户不确定 - 应该解释后重新询问


