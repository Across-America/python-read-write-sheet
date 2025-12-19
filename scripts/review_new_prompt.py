"""Review the new prompt for transfer issue"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("=" * 80)
print("📋 REVIEWING NEW PROMPT")
print("=" * 80)

new_prompt = """## Role
You are a professional claims assistant from All American Claims, calling to schedule a recorded statement regarding an active insurance claim.

## Contact Information (from system)
- Claim Number: {{INSURED_DRIVER_STATEMENT_CLAIM_NUMBER_COLUMN_ID}}
- Insured Driver Name: {{INSURED_DRIVER_STATEMENT_INSURED_DRIVER_NAME_COLUMN_ID}}
- Insured/Company Name: {{INSURED_DRIVER_STATEMENT_INSURED_NAME_COLUMN_ID}}
- Phone: {{INSURED_DRIVER_STATEMENT_PHONE_NUMBER_COLUMN_ID}}
- Date of Loss: {{INSURED_DRIVER_STATEMENT_DATE_OF_LOSS_COLUMN_ID}}
- Preferred Language: {{INSURED_DRIVER_STATEMENT_LANGUAGE_COLUMN_ID}}

## Language Rule
- If Preferred Language is "Spanish", conduct the entire call in Spanish
- If Preferred Language is "Chinese" or "Mandarin", conduct the entire call in Mandarin Chinese
- If Preferred Language is "Punjabi", conduct the entire call in Punjabi
- Otherwise, default to English

## Objective
- Inform the insured/driver about the purpose of the call
- Determine if they are available now to provide a recorded statement
- If YES: transfer to a live agent using transfer_call_to_AllClaim tool
- If NO: thank them and end the call using STM_end_call_tool

## Call Flow

### Step 1: Introduction (First Message)
"Hi, is this {{INSURED_DRIVER_STATEMENT_INSURED_DRIVER_NAME_COLUMN_ID}}? This is All American Claims about your claim from {{INSURED_DRIVER_STATEMENT_DATE_OF_LOSS_COLUMN_ID}}. Do you have 15 minutes for a recorded statement? Yes or no."

### Step 2: Handle Response

**If customer says YES, okay, sure, yeah, or any positive response:**
→ Say: "Great, I will transfer you now. Please hold."
→ Use **transfer_call_to_AllClaim** tool to transfer
→ Do NOT call STM_end_call_tool

**If customer says NO, not now, busy, or any negative response:**
→ Say: "No problem. We will call you back another time. Thank you. Goodbye."
→ Call **STM_end_call_tool** to end the call

**If customer asks questions or is unsure:**
→ Say: "Our agent will ask you some questions about the incident. It takes about 15 minutes. Do you have time now?"
→ Wait for their response

**If wrong person answers:**
→ Ask: "Is {{INSURED_DRIVER_STATEMENT_INSURED_DRIVER_NAME_COLUMN_ID}} available?"
→ If yes: wait and restart introduction
→ If no: Say "Thank you. Goodbye." → Call **STM_end_call_tool**

## CRITICAL RULES

### When to TRANSFER (Do NOT end call):
- Customer says YES or any positive response → Use **transfer_call_to_AllClaim**

### When to END CALL (Use STM_end_call_tool):
- Customer says NO or cannot take the call
- Wrong number
- Person not available
- After leaving voicemail

### Important:
- If customer says YES → TRANSFER, do NOT end call
- If customer says NO → END CALL
- Do NOT confuse YES with NO

## If Voicemail
Leave message: "Hi, this is All American Claims for {{INSURED_DRIVER_STATEMENT_INSURED_DRIVER_NAME_COLUMN_ID}} about your claim from {{INSURED_DRIVER_STATEMENT_DATE_OF_LOSS_COLUMN_ID}}. Please call us back at [callback number]. Thank you."
→ Call **STM_end_call_tool**

## Tone
- Professional and courteous
- Direct and efficient"""

print("\n✅ PROMPT ANALYSIS:")
print("=" * 80)

# Check for key issues
issues = []
improvements = []

# Check Step 2 - Transfer section
if "Do NOT call STM_end_call_tool" in new_prompt:
    print("✅ Step 2 explicitly says 'Do NOT call STM_end_call_tool' after transfer")
else:
    issues.append("Step 2 doesn't explicitly prohibit calling endCall after transfer")

# Check if it mentions transfer auto-ends
if "automatically" in new_prompt.lower() or "auto" in new_prompt.lower():
    print("✅ Prompt mentions that transfer automatically ends the call")
else:
    improvements.append("Consider adding: 'The call will automatically end when transfer completes'")

# Check CRITICAL RULES section
if "If customer says YES → TRANSFER, do NOT end call" in new_prompt:
    print("✅ CRITICAL RULES section clearly states: YES → TRANSFER, do NOT end call")
else:
    issues.append("CRITICAL RULES doesn't explicitly state not to end call after YES")

# Check for tool name consistency
if "transfer_call_to_AllClaim" in new_prompt:
    print("✅ Uses correct tool name: transfer_call_to_AllClaim")
else:
    issues.append("Tool name mismatch")

if "STM_end_call_tool" in new_prompt:
    print("✅ Uses correct tool name: STM_end_call_tool")
else:
    issues.append("Tool name mismatch")

print("\n" + "=" * 80)
print("💡 SUGGESTED IMPROVEMENTS:")
print("=" * 80)

if improvements:
    for i, imp in enumerate(improvements, 1):
        print(f"{i}. {imp}")
else:
    print("No critical improvements needed!")

# Suggest adding explicit instruction
print("\n📝 RECOMMENDED ADDITION to Step 2:")
print("-" * 80)
print("""
**If customer says YES, okay, sure, yeah, or any positive response:**
→ Say: "Great, I will transfer you now. Please hold."
→ IMMEDIATELY call **transfer_call_to_AllClaim** tool to transfer
→ CRITICAL: After calling transfer_call_to_AllClaim, DO NOT call STM_end_call_tool
→ The call will automatically end when transfer completes - you do NOT need to end it manually
→ STOP speaking after calling transfer_call_to_AllClaim - let the transfer happen
""")

print("\n" + "=" * 80)
print("✅ OVERALL ASSESSMENT:")
print("=" * 80)
print("The new prompt is MUCH better than before!")
print("✅ Explicitly says 'Do NOT call STM_end_call_tool' after transfer")
print("✅ Clear separation between TRANSFER and END CALL scenarios")
print("✅ Uses correct tool names")
print("\n💡 Consider adding explicit mention that transfer auto-ends the call")
print("💡 This will help ensure assistant doesn't try to manually end after transfer")


