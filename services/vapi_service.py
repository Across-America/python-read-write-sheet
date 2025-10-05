"""
VAPI Service - Handles all VAPI API interactions
"""

import requests
import time
import json
from datetime import datetime, timedelta
from config import VAPI_API_KEY, COMPANY_PHONE_NUMBER_ID
from config.settings import DEFAULT_CHECK_INTERVAL, DEFAULT_MAX_WAIT_TIME, ANALYSIS_WAIT_TIMEOUT
from utils import format_phone_number


class VAPIService:
    """Service for interacting with VAPI API"""

    def __init__(self, assistant_id):
        self.api_key = VAPI_API_KEY
        self.assistant_id = assistant_id
        self.phone_number_id = COMPANY_PHONE_NUMBER_ID
        self.base_url = "https://api.vapi.ai"
    
    def make_batch_call(self, customers, schedule_immediately=True):
        """
        Make batch VAPI call using the customers parameter
        
        Args:
            customers (list): List of customer records
            schedule_immediately (bool): If True, call immediately; if False, schedule for later
        
        Returns:
            dict: Call result information or None if failed
        """
        print(f"🚀 Making batch VAPI call to {len(customers)} customers")
        print(f"🤖 Using Spencer: Call Transfer V2 Campaign assistant")
        print(f"🏢 Company caller ID: +1 (951) 247-2003")
        
        # Prepare customers array for VAPI
        vapi_customers = []
        all_customer_contexts = []
        
        for customer in customers:
            formatted_phone = format_phone_number(customer['phone_number'])
            
            # Create customer context for VAPI
            customer_context = {
                "number": formatted_phone,
                "name": customer.get('insured', 'Customer')
            }
            
            # Create context for assistant overrides
            assistant_context = {
                "Insured": customer.get('insured', 'Customer'),
                "agent_name": customer.get('agent_name', 'Spencer'),
                "LOB": customer.get('lob', 'Insurance'),
                "Policy Number": customer.get('policy_number', ''),
                "Cancellation Date": customer.get('cancellation_date', ''),
                "office": customer.get('office', 'Insurance Office'),
                "status": customer.get('status', 'Active'),
                "cancellation_reason": customer.get('cancellation_reason', ''),
                "client_id": customer.get('client_id', '')
            }
            
            vapi_customers.append(customer_context)
            all_customer_contexts.append(assistant_context)
            
            print(f"   📞 {customer.get('insured', 'Unknown')} - {formatted_phone}")
            print(f"      Policy: {customer.get('policy_number', 'N/A')}")
            print(f"      Agent: {customer.get('agent_name', 'N/A')}")
            print(f"      LOB: {customer.get('lob', 'N/A')}")
        
        # Prepare payload
        payload = {
            "assistantId": self.assistant_id,
            "phoneNumberId": self.phone_number_id,
            "customers": vapi_customers,
            "assistantOverrides": {
                "variableValues": all_customer_contexts[0] if all_customer_contexts else {}
            }
        }
        
        # Add scheduling if not immediate
        if not schedule_immediately:
            schedule_time = datetime.now() + timedelta(hours=1)
            payload["schedulePlan"] = {
                "earliestAt": schedule_time.isoformat() + "Z"
            }
            print(f"⏰ Scheduled for: {schedule_time}")
        else:
            print(f"⚡ Calling immediately")
        
        try:
            response = requests.post(
                f"{self.base_url}/call",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            print(f"📡 Response Status: {response.status_code}")
            
            if 200 <= response.status_code < 300:
                result = response.json()
                print(f"✅ Batch call initiated successfully!")
                print(f"🔍 Response: {json.dumps(result, indent=2)}")
                
                # Extract call IDs
                call_ids = self._extract_call_ids(result)
                
                if call_ids:
                    print(f"\n📞 Monitoring {len(call_ids)} call(s)...")
                    for i, call_id in enumerate(call_ids, 1):
                        print(f"   Call {i}: {call_id}")
                    
                    # Monitor the first call
                    print(f"\n📡 Monitoring first call for summary...")
                    call_data = self.wait_for_call_completion(call_ids[0])
                    
                    if call_data:
                        self._display_call_results(call_data)
                        
                        return {
                            'success': True,
                            'call_ids': call_ids,
                            'call_data': call_data,
                            'result': result
                        }
                
                return {
                    'success': True,
                    'call_ids': call_ids,
                    'result': result
                }
            else:
                print(f"❌ Batch call failed with status: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error making batch call: {e}")
            return None
    
    def check_call_status(self, call_id):
        """
        Check call status from VAPI API
        
        Args:
            call_id (str): VAPI call ID
        
        Returns:
            dict: Call data or None if failed
        """
        try:
            response = requests.get(
                f"{self.base_url}/call/{call_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get call status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error checking call status: {e}")
            return None
    
    def wait_for_call_completion(self, call_id, check_interval=None, max_wait_time=None):
        """
        Wait for call to complete AND analysis to be generated
        
        Args:
            call_id (str): VAPI call ID
            check_interval (int): Seconds between status checks
            max_wait_time (int): Maximum wait time in seconds
        
        Returns:
            dict: Final call data with analysis or None if timeout/error
        """
        if check_interval is None:
            check_interval = DEFAULT_CHECK_INTERVAL
        if max_wait_time is None:
            max_wait_time = DEFAULT_MAX_WAIT_TIME
        
        print(f"⏳ Monitoring call status and waiting for analysis...")
        print(f"⏰ Checking every {check_interval} seconds")
        print(f"⏰ Maximum wait time: {max_wait_time} seconds")
        
        start_time = time.time()
        call_ended = False
        analysis_wait_start = 0
        
        while True:
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                print(f"⏰ Timeout reached ({max_wait_time}s). Stopping monitoring.")
                return None
            
            # Check call status
            call_data = self.check_call_status(call_id)
            if not call_data:
                print(f"❌ Failed to get call status. Retrying in {check_interval}s...")
                time.sleep(check_interval)
                continue
            
            status = call_data.get('status', 'unknown')
            print(f"📊 Call Status: {status} (elapsed: {int(elapsed_time)}s)")
            
            # Check if call ended
            if status == 'ended' and not call_ended:
                self._display_call_end_info(call_data)
                call_ended = True
                analysis_wait_start = time.time()
                print(f"⏳ Call ended, waiting for VAPI analysis to complete...")
                continue
            
            # Check for analysis after call ended
            if call_ended:
                analysis_elapsed = time.time() - analysis_wait_start
                
                if self._check_analysis_complete(call_data):
                    print(f"📝 Analysis completed after {int(analysis_elapsed)}s!")
                    return call_data
                elif analysis_elapsed > ANALYSIS_WAIT_TIMEOUT:
                    print(f"⏰ Analysis wait timeout ({ANALYSIS_WAIT_TIMEOUT}s). Returning with current data.")
                    return call_data
                else:
                    print(f"⏳ Analysis still processing... ({int(analysis_elapsed)}s elapsed)")
                    time.sleep(check_interval)
                    continue
            
            # Call still active
            print(f"⏳ Call still active. Checking again in {check_interval}s...")
            time.sleep(check_interval)
    
    def _extract_call_ids(self, result):
        """Extract call IDs from API response"""
        call_ids = []
        if 'results' in result and isinstance(result['results'], list):
            for call_result in result['results']:
                if 'id' in call_result:
                    call_ids.append(call_result['id'])
        elif 'id' in result:
            call_ids.append(result['id'])
        return call_ids
    
    def _display_call_end_info(self, call_data):
        """Display call end information"""
        print(f"✅ Call completed!")
        ended_reason = call_data.get('endedReason', 'unknown')
        duration = call_data.get('duration', 0)
        cost = call_data.get('cost', 0)
        print(f"📋 End Reason: {ended_reason}")
        print(f"⏱️ Duration: {duration} seconds")
        print(f"💰 Cost: ${cost:.4f}")
    
    def _check_analysis_complete(self, call_data):
        """Check if analysis is complete"""
        analysis = call_data.get('analysis', {})
        summary = analysis.get('summary', '')
        structured_data = analysis.get('structuredData', {})
        success_evaluation = analysis.get('successEvaluation', '')
        
        has_summary = summary and len(summary.strip()) > 10
        has_structured_data = structured_data and len(str(structured_data)) > 10
        has_success_eval = success_evaluation and len(str(success_evaluation)) > 5
        
        if has_summary or has_structured_data or has_success_eval:
            print(f"   Summary: {'✅' if has_summary else '❌'}")
            print(f"   Structured Data: {'✅' if has_structured_data else '❌'}")
            print(f"   Success Evaluation: {'✅' if has_success_eval else '❌'}")
            return True
        return False
    
    def _display_call_results(self, call_data):
        """Display detailed call results"""
        print(f"\n✅ CALL MONITORING COMPLETED!")
        print(f"📊 Final Status: {call_data.get('status', 'unknown')}")
        print(f"📋 End Reason: {call_data.get('endedReason', 'unknown')}")
        print(f"💰 Cost: ${call_data.get('cost', 0):.4f}")
        print(f"⏱️ Duration: {call_data.get('duration', 0)} seconds")
        
        # Show analysis
        analysis = call_data.get('analysis', {})
        if analysis:
            print(f"\n📝 VAPI CALL ANALYSIS RESULTS:")
            print("=" * 50)
            
            summary = analysis.get('summary', '')
            if summary:
                print(f"📋 Summary:")
                print("-" * 30)
                print(summary)
                print("-" * 30)
            
            structured_data = analysis.get('structuredData', {})
            if structured_data:
                print(f"\n📊 Structured Data:")
                print("-" * 30)
                print(structured_data)
                print("-" * 30)
            
            success_evaluation = analysis.get('successEvaluation', '')
            if success_evaluation:
                print(f"\n🎯 Success Evaluation:")
                print("-" * 30)
                print(success_evaluation)
                print("-" * 30)
        
        # Show transcript
        transcript = call_data.get('transcript', '')
        if transcript:
            print(f"\n💬 Call Transcript:")
            print("-" * 40)
            print(transcript)
            print("-" * 40)
