# 🎯 VAPI Call Analysis Plan Configuration
# 保险取消电话专用分析配置

## 📋 **完整的 analysisPlan 配置**

```json
{
  "analysisPlan": {
    "summaryPrompt": "You are an expert insurance call analyst. Provide a precise 2-3 sentence summary of this call that answers: 1) WHO was contacted and if it was the right person 2) WHAT the customer's response was 3) WHAT the final outcome was. Be specific and factual. Examples: 'Reached correct customer John Smith who was upset about premium increase but agreed to payment plan starting next month. Policy will be maintained.' OR 'Wrong person answered - spoke to customer's spouse who said John moved out 6 months ago. Need to update contact information and locate correct customer.' OR 'Customer declined to discuss cancellation and hung up after 30 seconds. No resolution achieved, marked as uncooperative contact.'",
    
    "structuredDataPrompt": "Extract key information from this insurance cancellation call transcript. Focus on contact verification, customer responses, outcomes, and next steps.",
    
    "structuredDataSchema": {
      "type": "object",
      "properties": {
        "contactVerified": {
          "type": "boolean",
          "description": "Was the correct customer reached?"
        },
        "contactIssue": {
          "type": "string",
          "enum": ["correct_person", "wrong_person", "no_answer", "voicemail", "busy"],
          "description": "Contact verification result"
        },
        "customerResponse": {
          "type": "string",
          "enum": ["interested", "declined", "angry", "confused", "neutral", "cooperative"],
          "description": "Customer's attitude and response"
        },
        "callOutcome": {
          "type": "string",
          "enum": ["policy_maintained", "cancellation_confirmed", "payment_scheduled", "needs_followup", "transferred", "call_ended_early"],
          "description": "Final outcome of the call"
        },
        "issuesEncountered": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["wrong_contact_info", "customer_upset", "payment_problems", "technical_issues", "language_barrier", "none"]
          },
          "description": "Any problems during the call"
        },
        "nextSteps": {
          "type": "string",
          "enum": ["no_action", "schedule_callback", "send_information", "update_contact_info", "escalate_to_supervisor", "process_payment"],
          "description": "Required follow-up actions"
        },
        "paymentDiscussed": {
          "type": "boolean",
          "description": "Was payment or payment plan discussed?"
        },
        "customerConcerns": {
          "type": "string",
          "description": "Main concerns expressed by customer"
        }
      },
      "required": ["contactVerified", "contactIssue", "customerResponse", "callOutcome", "issuesEncountered", "nextSteps", "paymentDiscussed"]
    },
    
    "successEvaluationPrompt": "Evaluate this insurance cancellation call based on these criteria: 1) Was the correct customer contacted? 2) Did the agent address customer concerns professionally? 3) Was a positive outcome achieved (policy maintained, payment scheduled, or appropriate next steps)? 4) Were any significant issues encountered? A call is successful if the correct person was reached AND either the policy was maintained, payment was arranged, or appropriate follow-up was scheduled without major issues.",
    
    "successEvaluationRubric": "PassFail"
  }
}
```

## 🔧 **更新我们的代码以使用新的分析结果**

现在我们需要修改 `auto_call_and_update.py` 来使用VAPI的官方分析结果而不是简单的summary字段：

<function_calls>
<invoke name="search_replace">
<parameter name="file_path">/Users/rickyang/Desktop/python-read-write-sheet/auto_call_and_update.py
