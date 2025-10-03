#!/usr/bin/env python3
"""
Update VAPI assistant analysis plan to include structured data and success evaluation
"""

import requests
import json

VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"  # Spencer: Call Transfer V2 Campaign

def update_analysis_plan():
    """
    Update the VAPI assistant analysis plan to include:
    1. Summary Plan (already exists)
    2. Structured Data Plan (NEW)
    3. Success Evaluation Plan (NEW)
    """
    
    # Enhanced analysis plan with structured data and success evaluation
    enhanced_analysis_plan = {
        "summaryPlan": {
            "messages": [
                {
                    "content": "# Summary Agent for Non-Payment Notification Calls\n\n## [Identity]\nYou are a Summary Agent for All Solution Insurance.\nYour role is to provide a brief post-call summary after notifying customers about policy cancellation due to non-payment.\n\n## [Task & Goals]\n\n### Summarize Notification Call\n- Confirm that the customer was notified about the policy cancellation due to non-payment\n- Note the customer's immediate response (if any)\n- Record if the call was completed successfully\n\n### Document Transfer Status  \n- Confirm if the customer was transferred to an agent for assistance\n- Note if the customer declined transfer or disconnected\n- Indicate any follow-up required\n\n## [Response Guidelines]\n- Use a professional and objective tone\n- Keep the summary VERY brief (2-4 sentences max per section)\n- Use bullet points or short phrases when possible\n- Focus only on key outcomes, not detailed conversation flow\n- Structure the output in two clear sections: Conversation Summary and Transfer Outcome\n\n## [Output Format]\n\n**Call Summary:**\nCustomer [Name] was successfully notified that policy [#] will be cancelled due to non-payment of $[Amount] due on [Date]. [Brief customer response if applicable].\n\n**Transfer Outcome:**\nCustomer was transferred to billing agent for assistance. / Customer declined transfer. / Customer disconnected before transfer.\n\n## [Sample Outputs]\n\n**Example 1:**\nConversation Summary: Customer notified of policy cancellation due to non-payment. Customer accepted transfer.\nTransfer Outcome: Successfully transferred to billing agent.\n\n**Example 2:**\nConversation Summary: Customer notified of policy cancellation. Customer wanted to cancel policy voluntarily.\nTransfer Outcome: No transfer needed. Customer ended call.\n\n**Example 3:**\nConversation Summary: Customer notified of non-payment cancellation. Customer asked for policy details.\nTransfer Outcome: Customer disconnected before transfer completed.",
                    "role": "system"
                },
                {
                    "content": "Here is the transcript:\n\n{{transcript}}\n\n. Here is the ended reason of the call:\n\n{{endedReason}}\n\n",
                    "role": "user"
                }
            ]
        },
        "structuredDataPlan": {
            "messages": [
                {
                    "content": "# Structured Data Extraction Agent\n\n## [Identity]\nYou are a Data Extraction Agent for All Solution Insurance.\nYour role is to extract key structured information from non-payment notification calls.\n\n## [Task & Goals]\n\nExtract the following key data points from the call:\n\n1. **Call Outcome**\n   - transfer_requested: boolean (did customer ask for or accept transfer?)\n   - transfer_completed: boolean (was transfer successful?)\n   - customer_ended_call: boolean (did customer hang up?)\n\n2. **Customer Response**\n   - payment_status_claimed: string (what did customer say about payment? e.g., \"already paid\", \"will pay\", \"cannot pay\", \"not mentioned\")\n   - questions_asked: array of strings (what questions did customer ask?)\n   - concerns_raised: array of strings (what concerns did customer raise?)\n\n3. **Call Quality**\n   - customer_understood: boolean (did customer understand the notification?)\n   - customer_engaged: boolean (did customer actively participate?)\n   - call_duration_appropriate: boolean (was call duration reasonable?)\n\n4. **Follow-up Required**\n   - callback_requested: boolean\n   - escalation_needed: boolean\n   - notes: string (any important notes for follow-up)\n\n## [Output Format]\nReturn ONLY valid JSON with the following structure:\n\n```json\n{\n  \"call_outcome\": {\n    \"transfer_requested\": boolean,\n    \"transfer_completed\": boolean,\n    \"customer_ended_call\": boolean\n  },\n  \"customer_response\": {\n    \"payment_status_claimed\": string,\n    \"questions_asked\": [string],\n    \"concerns_raised\": [string]\n  },\n  \"call_quality\": {\n    \"customer_understood\": boolean,\n    \"customer_engaged\": boolean,\n    \"call_duration_appropriate\": boolean\n  },\n  \"follow_up\": {\n    \"callback_requested\": boolean,\n    \"escalation_needed\": boolean,\n    \"notes\": string\n  }\n}\n```",
                    "role": "system"
                },
                {
                    "content": "Here is the transcript:\n\n{{transcript}}\n\nHere is the ended reason of the call:\n\n{{endedReason}}\n\nExtract the structured data from this call.",
                    "role": "user"
                }
            ],
            "schema": {
                "type": "object",
                "properties": {
                    "call_outcome": {
                        "type": "object",
                        "properties": {
                            "transfer_requested": {"type": "boolean"},
                            "transfer_completed": {"type": "boolean"},
                            "customer_ended_call": {"type": "boolean"}
                        }
                    },
                    "customer_response": {
                        "type": "object",
                        "properties": {
                            "payment_status_claimed": {"type": "string"},
                            "questions_asked": {"type": "array", "items": {"type": "string"}},
                            "concerns_raised": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "call_quality": {
                        "type": "object",
                        "properties": {
                            "customer_understood": {"type": "boolean"},
                            "customer_engaged": {"type": "boolean"},
                            "call_duration_appropriate": {"type": "boolean"}
                        }
                    },
                    "follow_up": {
                        "type": "object",
                        "properties": {
                            "callback_requested": {"type": "boolean"},
                            "escalation_needed": {"type": "boolean"},
                            "notes": {"type": "string"}
                        }
                    }
                }
            }
        },
        "successEvaluationPlan": {
            "messages": [
                {
                    "content": "# Success Evaluation Agent\n\n## [Identity]\nYou are a Success Evaluation Agent for All Solution Insurance.\nYour role is to evaluate the success of non-payment notification calls.\n\n## [Task & Goals]\n\nEvaluate the call's success based on these criteria:\n\n1. **Primary Goal Achievement (50%)**\n   - Was customer successfully notified about cancellation?\n   - Did customer understand the reason (non-payment)?\n\n2. **Secondary Goal Achievement (30%)**\n   - Was transfer offered?\n   - Did customer accept or decline transfer clearly?\n\n3. **Call Quality (20%)**\n   - Was the call professional and clear?\n   - Did the agent follow the script?\n   - Was the customer treated with respect?\n\n## [Success Criteria]\n- **Successful**: Customer notified, understood reason, and made clear decision about transfer\n- **Partially Successful**: Customer notified but unclear response or early hangup\n- **Unsuccessful**: Customer not properly notified or major issues in call\n\n## [Output Format]\nReturn a boolean (true/false) and a brief reason.\n\n- true: Call was successful (customer properly notified and responded)\n- false: Call was unsuccessful (customer not notified or major issues)\n\nProvide reasoning in 1-2 sentences.",
                    "role": "system"
                },
                {
                    "content": "Here is the transcript:\n\n{{transcript}}\n\nHere is the ended reason of the call:\n\n{{endedReason}}\n\nEvaluate if this call was successful.",
                    "role": "user"
                }
            ]
        }
    }
    
    # Prepare the update payload
    payload = {
        "analysisPlan": enhanced_analysis_plan
    }
    
    print("🔧 UPDATING VAPI ASSISTANT ANALYSIS PLAN")
    print("=" * 60)
    print(f"Assistant ID: {ASSISTANT_ID}")
    print(f"Adding:")
    print("  ✅ Summary Plan (existing)")
    print("  🆕 Structured Data Plan")
    print("  🆕 Success Evaluation Plan")
    print("=" * 60)
    
    try:
        response = requests.patch(
            f"https://api.vapi.ai/assistant/{ASSISTANT_ID}",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if 200 <= response.status_code < 300:
            result = response.json()
            print(f"✅ Successfully updated analysis plan!")
            print(f"\n📝 Updated Analysis Plan:")
            print(json.dumps(result.get("analysisPlan", {}), indent=2))
            return True
        else:
            print(f"❌ Failed to update analysis plan")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating analysis plan: {e}")
        return False

if __name__ == "__main__":
    print("🧪 VAPI ASSISTANT ANALYSIS PLAN UPDATE")
    print("=" * 60)
    print("This script will update the Spencer assistant with:")
    print("  - Enhanced Summary Plan")
    print("  - Structured Data Extraction")
    print("  - Success Evaluation")
    print("=" * 60)
    print()
    
    success = update_analysis_plan()
    
    if success:
        print(f"\n🎉 ANALYSIS PLAN UPDATE COMPLETED!")
        print(f"✅ The Spencer assistant now has enhanced call analysis")
        print(f"📊 Future calls will include:")
        print(f"   - Summary (existing)")
        print(f"   - Structured Data (NEW)")
        print(f"   - Success Evaluation (NEW)")
    else:
        print(f"\n❌ ANALYSIS PLAN UPDATE FAILED!")
        print(f"💡 Check the error messages above for details")

