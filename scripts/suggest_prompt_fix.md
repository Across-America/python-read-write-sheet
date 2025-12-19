# Prompt Fix Suggestion

## Problem
Assistant recognizes "yes" but calls endCall instead of transfer tool.

## Current Step 2:
```
**If YES (available now):**
→ Proceed to Step 3 (Transfer)
```

## Issue
The instruction "Proceed to Step 3" is not explicit enough. Assistant might:
1. Say the transfer message
2. Think transfer is done
3. Call endCall immediately

## Suggested Fix for Step 2:

Change from:
```
**If YES (available now):**
→ Proceed to Step 3 (Transfer)
```

To:
```
**If YES (available now):**
→ IMMEDIATELY call **transfer_call_to_AllClaim** tool
→ Do NOT call STM_end_call_tool until AFTER transfer completes
→ After transfer completes, then call **STM_end_call_tool**
```

Or even more explicit:
```
**If YES (available now):**
→ Say: "Great, I will now transfer you to one of our agents..."
→ IMMEDIATELY call **transfer_call_to_AllClaim** tool (DO NOT skip this step!)
→ Wait for transfer to complete
→ After transfer completes, call **STM_end_call_tool**
```

## Key Changes:
1. Explicitly state to call transfer tool IMMEDIATELY
2. Emphasize NOT to call endCall until AFTER transfer
3. Make it clear that calling transfer tool is mandatory, not optional



