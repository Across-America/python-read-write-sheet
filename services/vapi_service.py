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


def format_amount_for_speech(amount_str):
    """
    Convert amount string to natural speech format

    Examples:
        "$500.00" -> "five hundred dollars"
        "500.00" -> "five hundred dollars"
        "1234.56" -> "one thousand two hundred thirty-four dollars and fifty-six cents"

    Args:
        amount_str: Amount string (may include $ sign)

    Returns:
        str: Natural language amount
    """
    if not amount_str:
        return "zero dollars"

    # Remove $ and whitespace
    clean_amount = str(amount_str).replace('$', '').replace(',', '').strip()

    try:
        # Parse to float
        amount = float(clean_amount)

        # Split into dollars and cents
        dollars = int(amount)
        cents = int(round((amount - dollars) * 100))

        # Convert to words
        dollar_words = number_to_words(dollars)

        if cents == 0:
            return f"{dollar_words} dollars"
        else:
            cent_words = number_to_words(cents)
            return f"{dollar_words} dollars and {cent_words} cents"
    except (ValueError, TypeError):
        return amount_str  # Return original if parsing fails


def number_to_words(n):
    """Convert number to words (0-999999)"""
    if n == 0:
        return "zero"

    ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
             "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

    def convert_below_thousand(num):
        if num == 0:
            return ""
        elif num < 10:
            return ones[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            return tens[num // 10] + ("-" + ones[num % 10] if num % 10 != 0 else "")
        else:
            return ones[num // 100] + " hundred" + (" " + convert_below_thousand(num % 100) if num % 100 != 0 else "")

    if n < 1000:
        return convert_below_thousand(n)
    elif n < 1000000:
        thousands = n // 1000
        remainder = n % 1000
        result = convert_below_thousand(thousands) + " thousand"
        if remainder > 0:
            result += " " + convert_below_thousand(remainder)
        return result
    else:
        return str(n)  # Fallback for very large numbers


def format_date_for_speech(date_str):
    """
    Convert date string to natural speech format

    Examples:
        "2025-10-27" -> "October 27, 2025"
        "10/27/2025" -> "October 27, 2025"

    Args:
        date_str: Date string in various formats

    Returns:
        str: Natural language date
    """
    if not date_str:
        return ""

    # Try multiple date formats
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%m/%d/%y',
        '%Y/%m/%d'
    ]

    for fmt in formats:
        try:
            date_obj = datetime.strptime(str(date_str).strip(), fmt)
            # Format as "October 27, 2025"
            return date_obj.strftime('%B %d, %Y')
        except ValueError:
            continue

    return date_str  # Return original if parsing fails


def expand_lob_abbreviation(lob_abbrev):
    """
    Expand LOB abbreviation to full form for speech
    
    Examples:
        "MHOME" -> "Mobile home"
        "HOME" -> "Home"
        "AUTOP" -> "Auto"
        "FLOOD" -> "Flood"
    
    Args:
        lob_abbrev: LOB abbreviation from Smartsheet
    
    Returns:
        str: Full form of LOB for speech (e.g., "Mobile home policy")
    """
    if not lob_abbrev:
        return ""
    
    lob_upper = str(lob_abbrev).strip().upper()
    
    # LOB abbreviation to full form mapping
    # Based on user-provided mapping table and N1 Project sheet values
    lob_mapping = {
        # User-provided mappings (all HO types end with "Home")
        "HO3": "Primary Home",
        "HO4": "Renters Home",
        "HO6": "Condo Home",
        "DP3": "Landlord",
        "MHOME": "Mobile home",
        # Existing sheet values
        "HOME": "Home",
        "AUTOP": "Auto",
        "FLOOD": "Flood",
        "EQ": "Earthquake",
        "DFIRE": "Dwelling fire",
        "CPL": "Commercial package",
        "PROP": "Property",
        "PUMBR": "Personal umbrella",
        # Add more mappings as needed
    }
    
    # Check exact match first
    if lob_upper in lob_mapping:
        return lob_mapping[lob_upper]
    
    # Check if it contains any abbreviation
    for abbrev, full_form in lob_mapping.items():
        if abbrev in lob_upper:
            return full_form
    
    # If no mapping found, return original (capitalize first letter of each word)
    return lob_abbrev.title()


class VAPIService:
    """Service for interacting with VAPI API"""

    def __init__(self, assistant_id=None, phone_number_id=None):
        self.api_key = VAPI_API_KEY
        self.assistant_id = assistant_id
        # Use provided phone_number_id, or fall back to default company number
        self.phone_number_id = phone_number_id or COMPANY_PHONE_NUMBER_ID
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
            
            # Get customer name and truncate to 40 characters (VAPI API requirement)
            customer_name = customer.get('insured', 'Customer')
            if len(customer_name) > 40:
                customer_name = customer_name[:37] + "..."  # Truncate to 37 chars + "..." = 40 total
            
            # Create customer context for VAPI
            customer_context = {
                "number": formatted_phone,
                "name": customer_name
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
                    
                    # Monitor the first call (skip if skip_wait=True for faster calling)
                    if skip_wait:
                        print(f"\n⚡ Skipping wait - returning immediately for faster calling")
                        # Just get initial call status without waiting
                        call_data = self.check_call_status(call_ids[0])
                        if call_data:
                            return [call_data]  # Return as list for consistency with other workflows
                        else:
                            # Return minimal call data with just the ID
                            return [{
                                'id': call_ids[0],
                                'status': 'initiated'
                            }]
                    else:
                        print(f"\n📡 Monitoring first call for summary...")
                        call_data = self.wait_for_call_completion(call_ids[0])
                        
                        if call_data:
                            self._display_call_results(call_data)
                            # Return as list for consistency
                            return [call_data]
                
                # If no call_ids but successful, return empty list
                return []
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

                # Check if this is a no-answer scenario (no analysis expected)
                end_reason = call_data.get('endedReason', '')
                no_analysis_reasons = [
                    'customer-did-not-answer',
                    'customer-did-not-give-microphone-permission',
                    'customer-busy',
                    'voicemail',
                    'assistant-error',
                    'twilio-failed-to-connect-call'
                ]

                if end_reason in no_analysis_reasons:
                    print(f"⚠️  Call ended without conversation ({end_reason})")
                    print(f"📝 No analysis expected for this call type")
                    return call_data

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

        # Calculate duration from timestamps if not provided
        if duration == 0 or duration is None:
            started_at = call_data.get('startedAt')
            ended_at = call_data.get('endedAt')
            if started_at and ended_at:
                from datetime import datetime
                try:
                    start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(ended_at.replace('Z', '+00:00'))
                    duration = (end - start).total_seconds()
                except:
                    pass

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

        # Calculate duration from timestamps if not provided
        duration = call_data.get('duration', 0)
        if duration == 0 or duration is None:
            started_at = call_data.get('startedAt')
            ended_at = call_data.get('endedAt')
            if started_at and ended_at:
                from datetime import datetime
                try:
                    start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(ended_at.replace('Z', '+00:00'))
                    duration = (end - start).total_seconds()
                except:
                    pass

        print(f"⏱️ Duration: {duration} seconds")
        
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

    def make_batch_call_with_assistant(self, customers, assistant_id, schedule_immediately=True, schedule_at=None, max_retries=3, custom_variable_builder=None, skip_wait=False):
        """
        Make batch VAPI call with a specific assistant ID

        Args:
            customers (list): List of customer records
            assistant_id (str): Specific assistant ID to use for this batch
            schedule_immediately (bool): If True, call immediately (default: True)
            schedule_at (datetime): Specific datetime to schedule the call (overrides schedule_immediately)
            custom_variable_builder (callable): Optional function to build custom variable values.
                                               Function signature: (customer) -> dict
                                               If provided, uses this instead of default renewal workflow variables

        Returns:
            list: List of call result dicts or None if failed
        """
        print(f"🚀 Making batch VAPI call to {len(customers)} customers")
        print(f"🤖 Using Assistant ID: {assistant_id}")
        print(f"🏢 Company caller ID: +1 (951) 247-2003")
        
        # Prepare customers array for VAPI
        vapi_customers = []

        # Prepare assistant overrides with customer-specific variables
        # Use first customer's data for variable values (for batch calls)
        first_customer = customers[0] if customers else {}
        
        # Use custom variable builder if provided, otherwise use default renewal workflow variables
        if custom_variable_builder:
            variable_values = custom_variable_builder(first_customer)
            assistant_overrides = {
                "variableValues": variable_values
            }
        else:
            # Default renewal workflow variable building
            # Get offered_premium and format it for speech if available
            # For renewal workflow, amount_due and renewal_payment should use the same value (offered_premium)
            offered_premium = first_customer.get('offered_premium', '') or first_customer.get('Offered Premium', '')
            
            # Use offered_premium for amount_due if available, otherwise fall back to amount_due field
            amount_due_value = offered_premium if offered_premium else first_customer.get('amount_due', '0')
            
            # Format amounts for speech
            amount_due_formatted = format_amount_for_speech(amount_due_value)
            renewal_payment = amount_due_formatted  # Same value as amount_due
            
            # Get expiration date and format it for speech
            expiration_date_str = first_customer.get('expiration_date', '') or first_customer.get('expiration date', '')
            expiration_date_formatted = format_date_for_speech(expiration_date_str) if expiration_date_str else ''
            
            assistant_overrides = {
                "variableValues": {
                    "company": first_customer.get('company', 'Customer'),
                    "Company": first_customer.get('company', 'Customer'),  # Support both lowercase and capitalized
                    "amount_due": amount_due_formatted,  # Use offered_premium if available
                    "cancellation_date": format_date_for_speech(first_customer.get('cancellation_date', '')),
                    "phone_number": first_customer.get('phone_number', ''),
                    "policy_number": first_customer.get('policy_number', ''),
                    "client_id": first_customer.get('client_id', ''),
                    "renewal_payment": renewal_payment,  # Same as amount_due (both use offered_premium)
                    # Variables for first message - using underscore format (matching VAPI Assistant after user's update)
                    "First_Name": first_customer.get('first_name', '') or first_customer.get('First Name', ''),
                    "first_name": first_customer.get('first_name', '') or first_customer.get('First Name', ''),
                    "Last_Name": first_customer.get('last_name', '') or first_customer.get('Last Name', ''),
                    "last_name": first_customer.get('last_name', '') or first_customer.get('Last Name', ''),
                    # Expand LOB abbreviation to full form for speech (e.g., "MHOME" -> "Mobile home")
                    "LOB": expand_lob_abbreviation(first_customer.get('lob', '') or first_customer.get('LOB', '')),
                    "lob": expand_lob_abbreviation(first_customer.get('lob', '') or first_customer.get('LOB', '')),
                    "Company": first_customer.get('company', 'Customer'),
                    "company": first_customer.get('company', 'Customer'),
                    "Expiration_Date": expiration_date_formatted,
                    "expiration_date": expiration_date_formatted,
                    # Also keep space versions for backward compatibility (in case assistant still uses them)
                    "First Name": first_customer.get('first_name', '') or first_customer.get('First Name', ''),
                    "Last Name": first_customer.get('last_name', '') or first_customer.get('Last Name', ''),
                    "Expiration Date": expiration_date_formatted,
                    "renewal payment": renewal_payment
                }
            }

        for customer in customers:
            # Support multiple phone field names (phone_number, contact_phone, etc.)
            phone = customer.get('phone_number') or customer.get('contact_phone') or customer.get('client_phone_number', '')
            if not phone:
                print(f"⚠️  Warning: Customer {customer.get('company', customer.get('insured_name', 'Unknown'))} has no phone number, skipping")
                continue
            
            # Skip phone numbers starting with 52 (Mexico country code)
            # Only skip if it's actually a Mexico number (starts with +52 or 52 with more than 10 digits)
            # Don't skip US numbers that happen to start with 52 (like area code 552)
            phone_cleaned = str(phone).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("/", "")
            if phone_cleaned.startswith('+52'):
                print(f"⚠️  Warning: Customer {customer.get('company', customer.get('insured_name', 'Unknown'))} has Mexico phone number ({phone}), skipping")
                continue
            # If it starts with 52 but has more than 10 digits, it's likely a Mexico number
            if phone_cleaned.startswith('52') and len(phone_cleaned) > 10:
                print(f"⚠️  Warning: Customer {customer.get('company', customer.get('insured_name', 'Unknown'))} has Mexico phone number ({phone}), skipping")
                continue
            
            formatted_phone = format_phone_number(phone)

            # Get customer name and truncate to 40 characters (VAPI API requirement)
            customer_name = customer.get('company', customer.get('insured_name', customer.get('insured', 'Customer')))
            if len(customer_name) > 40:
                customer_name = customer_name[:37] + "..."  # Truncate to 37 chars + "..." = 40 total
            
            # Create customer context for VAPI
            customer_context = {
                "number": formatted_phone,
                "name": customer_name
            }

            vapi_customers.append(customer_context)

            # Format amount for display (remove $ if already present)
            amount_display = customer.get('amount_due', 'N/A')
            if amount_display and not str(amount_display).startswith('$'):
                amount_display = f"${amount_display}"

            # Get offered premium for this customer
            customer_premium = customer.get('offered_premium', '') or customer.get('Offered Premium', '')
            
            # Get expiration date for display
            expiration_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
            expiration_display = format_date_for_speech(expiration_date_str) if expiration_date_str else 'N/A'
            
            # Format renewal payment for display
            renewal_payment_display = ''
            if customer_premium:
                renewal_payment_display = format_amount_for_speech(customer_premium)
            
            print(f"   📞 {customer.get('company', 'Unknown')} - {formatted_phone}")
            print(f"      Amount Due: {amount_display}")
            print(f"      Cancellation Date: {customer.get('cancellation_date', 'N/A')}")
            print(f"      Renewal Date (Expiration Date): {expiration_display}")
            if customer_premium:
                print(f"      Offered Premium: {customer_premium}")
                print(f"      Renewal Payment (formatted): {renewal_payment_display}")

        # Debug: Print variable values being sent
        print(f"\n📋 传递给 VAPI 的变量值:")
        print("-" * 80)
        for key, value in assistant_overrides.get("variableValues", {}).items():
            if value:  # Only show non-empty values
                print(f"  {key}: {value}")
        print("-" * 80)
        
        # 调试：显示 First Message 中使用的关键变量
        # 检查是否是STM1 workflow（通过检查是否有STM1特有的变量）
        variable_values = assistant_overrides.get("variableValues", {})
        is_stm1_workflow = "INSURED_DRIVER_STATEMENT_CLAIM_NUMBER_COLUMN_ID" in variable_values
        
        # 特别显示 renewal date 和 renewal amount（仅对Renewal workflow）
        if not is_stm1_workflow:
            print(f"\n💰 Renewal 信息:")
            print("-" * 80)
            renewal_payment_var = variable_values.get("renewal payment") or variable_values.get("renewal_payment", "")
            expiration_date_var = variable_values.get("Expiration Date") or variable_values.get("expiration_date", "")
            print(f"  Renewal Date: {expiration_date_var if expiration_date_var else '(空)'}")
            print(f"  Renewal Amount: {renewal_payment_var if renewal_payment_var else '(空)'}")
            print("-" * 80)
        
        if is_stm1_workflow:
            # STM1 workflow - 检查STM1特有的变量
            print(f"\n🔍 First Message 关键变量检查 (STM1):")
            print("-" * 80)
            stm1_vars = {
                "INSURED_DRIVER_STATEMENT_CLAIM_NUMBER_COLUMN_ID": variable_values.get("INSURED_DRIVER_STATEMENT_CLAIM_NUMBER_COLUMN_ID", ""),
                "INSURED_DRIVER_STATEMENT_INSURED_DRIVER_NAME_COLUMN_ID": variable_values.get("INSURED_DRIVER_STATEMENT_INSURED_DRIVER_NAME_COLUMN_ID", ""),
                "INSURED_DRIVER_STATEMENT_INSURED_NAME_COLUMN_ID": variable_values.get("INSURED_DRIVER_STATEMENT_INSURED_NAME_COLUMN_ID", ""),
                "INSURED_DRIVER_STATEMENT_DATE_OF_LOSS_COLUMN_ID": variable_values.get("INSURED_DRIVER_STATEMENT_DATE_OF_LOSS_COLUMN_ID", ""),
                "INSURED_DRIVER_STATEMENT_LANGUAGE_COLUMN_ID": variable_values.get("INSURED_DRIVER_STATEMENT_LANGUAGE_COLUMN_ID", ""),
            }
            for var_name, var_value in stm1_vars.items():
                status = "✅" if var_value else "❌"
                print(f"  {status} {{{{ {var_name} }}}}: {var_value if var_value else '(空 - 可能导致替换失败)'}")
            print("-" * 80)
        else:
            # Renewal/Non-Renewal workflow - 检查Renewal特有的变量
            renewal_payment_var = variable_values.get("renewal payment") or variable_values.get("renewal_payment", "")
            expiration_date_var = variable_values.get("Expiration Date") or variable_values.get("expiration_date", "")
            
            print(f"\n🔍 First Message 关键变量检查 (下划线格式):")
            print("-" * 80)
            first_message_vars_underscore = {
                "First_Name": variable_values.get("First_Name", ""),
                "Last_Name": variable_values.get("Last_Name", ""),
                "LOB": variable_values.get("LOB", ""),
                "Company": variable_values.get("Company", ""),
                "Expiration_Date": variable_values.get("Expiration_Date", ""),
                "renewal_payment": renewal_payment_var
            }
            for var_name, var_value in first_message_vars_underscore.items():
                status = "✅" if var_value else "❌"
                print(f"  {status} {{{{ {var_name} }}}}: {var_value if var_value else '(空 - 可能导致替换失败)'}")
            print("-" * 80)
            
            # 也显示空格版本（向后兼容）
            print(f"\n🔍 First Message 关键变量检查 (空格格式 - 向后兼容):")
            print("-" * 80)
            first_message_vars_space = {
                "First Name": variable_values.get("First Name", ""),
                "Last Name": variable_values.get("Last Name", ""),
                "LOB": variable_values.get("LOB", ""),
                "Company": variable_values.get("Company", ""),
                "Expiration Date": expiration_date_var,
                "renewal payment": renewal_payment_var
            }
            for var_name, var_value in first_message_vars_space.items():
                status = "✅" if var_value else "❌"
                print(f"  {status} {{{{ {var_name} }}}}: {var_value if var_value else '(空 - 可能导致替换失败)'}")
            print("-" * 80)
        
        # 调试：显示完整的 payload（仅变量部分）
        import json
        print(f"\n📦 完整 variableValues (JSON):")
        print("-" * 80)
        print(json.dumps(assistant_overrides.get("variableValues", {}), indent=2, ensure_ascii=False))
        print("-" * 80)
        
        # Debug: Check customers[52] and customers[94] if they exist
        if len(vapi_customers) > 52:
            print(f"\n🔍 DEBUG: customers[52]:")
            print(f"   Number: {vapi_customers[52].get('number', 'N/A')}")
            print(f"   Number repr: {repr(vapi_customers[52].get('number', 'N/A'))}")
            print(f"   Name: {vapi_customers[52].get('name', 'N/A')}")
            print(f"   Number type: {type(vapi_customers[52].get('number', 'N/A'))}")
            print(f"   Number length: {len(vapi_customers[52].get('number', ''))}")
        if len(vapi_customers) > 94:
            print(f"\n🔍 DEBUG: customers[94]:")
            print(f"   Number: {vapi_customers[94].get('number', 'N/A')}")
            print(f"   Number repr: {repr(vapi_customers[94].get('number', 'N/A'))}")
            print(f"   Name: {vapi_customers[94].get('name', 'N/A')}")
            print(f"   Number type: {type(vapi_customers[94].get('number', 'N/A'))}")
            print(f"   Number length: {len(vapi_customers[94].get('number', ''))}")
        
        # Prepare payload with the specified assistant
        payload = {
            "assistantId": assistant_id,
            "phoneNumberId": self.phone_number_id,
            "customers": vapi_customers,
            "assistantOverrides": assistant_overrides
        }
        
        # Add scheduling if specified
        if schedule_at:
            # Use specific datetime if provided
            payload["schedulePlan"] = {
                "earliestAt": schedule_at.isoformat() + "Z"
            }
            print(f"⏰ Scheduled for: {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
        elif not schedule_immediately:
            # Default to 1 hour from now if not immediate
            schedule_time = datetime.now() + timedelta(hours=1)
            payload["schedulePlan"] = {
                "earliestAt": schedule_time.isoformat() + "Z"
            }
            print(f"⏰ Scheduled for: {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"⚡ Calling immediately")
        
        # Split into smaller batches if too many customers (VAPI may have batch size limits)
        # Try processing in batches of 50 to avoid API limits
        MAX_BATCH_SIZE = 50
        if len(vapi_customers) > MAX_BATCH_SIZE:
            print(f"\n⚠️  Large batch detected ({len(vapi_customers)} customers). Splitting into batches of {MAX_BATCH_SIZE}...")
            all_results = []
            for batch_start in range(0, len(vapi_customers), MAX_BATCH_SIZE):
                batch_end = min(batch_start + MAX_BATCH_SIZE, len(vapi_customers))
                batch_customers = vapi_customers[batch_start:batch_end]
                print(f"\n📦 Processing batch {batch_start // MAX_BATCH_SIZE + 1}: customers {batch_start} to {batch_end - 1}")
                
                batch_payload = {
                    "assistantId": assistant_id,
                    "phoneNumberId": self.phone_number_id,
                    "customers": batch_customers,
                    "assistantOverrides": assistant_overrides
                }
                
                # Add scheduling
                if schedule_at:
                    batch_payload["schedulePlan"] = {
                        "earliestAt": schedule_at.isoformat() + "Z"
                    }
                elif not schedule_immediately:
                    schedule_time = datetime.now() + timedelta(hours=1)
                    batch_payload["schedulePlan"] = {
                        "earliestAt": schedule_time.isoformat() + "Z"
                    }
                
                # Make batch request
                try:
                    batch_response = requests.post(
                        f"{self.base_url}/call",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json=batch_payload,
                        timeout=30
                    )
                    
                    print(f"📡 Batch {batch_start // MAX_BATCH_SIZE + 1} Response Status: {batch_response.status_code}")
                    
                    if batch_response.status_code in [200, 201]:
                        batch_data = batch_response.json()
                        call_ids = self._extract_call_ids(batch_data)
                        if call_ids:
                            all_results.extend([{'id': cid} for cid in call_ids])
                        print(f"✅ Batch {batch_start // MAX_BATCH_SIZE + 1} completed successfully")
                    else:
                        error_data = batch_response.json() if batch_response.headers.get('content-type', '').startswith('application/json') else {}
                        # Extract Request ID
                        request_id = batch_response.headers.get('X-Request-ID') or batch_response.headers.get('Request-ID') or batch_response.headers.get('x-request-id')
                        if not request_id and isinstance(error_data, dict):
                            request_id = error_data.get('requestId') or error_data.get('request_id') or error_data.get('id')
                        
                        error_msg = error_data.get('message', batch_response.text[:200]) if isinstance(error_data, dict) else batch_response.text[:200]
                        print(f"❌ Batch {batch_start // MAX_BATCH_SIZE + 1} failed: {error_msg}")
                        if request_id:
                            print(f"   🔍 Request ID: {request_id}")
                        # Continue with next batch even if one fails
                    
                    # Small delay between batches
                    if batch_end < len(vapi_customers):
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"❌ Batch {batch_start // MAX_BATCH_SIZE + 1} error: {e}")
                    # Continue with next batch
            
            if all_results:
                return all_results
            else:
                return None
        
        # Retry logic for API calls (for smaller batches)
        import time
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/call",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30  # 30 second timeout
                )
                
                print(f"📡 API Response Status: {response.status_code}")
                
                # Debug: Print full response for errors
                if response.status_code >= 400:
                    # Extract Request ID from headers if present
                    request_id = response.headers.get('X-Request-ID') or response.headers.get('Request-ID') or response.headers.get('x-request-id')
                    
                    try:
                        error_data = response.json()
                        # Also check for Request ID in response body
                        if not request_id:
                            request_id = error_data.get('requestId') or error_data.get('request_id') or error_data.get('id') or error_data.get('error', {}).get('requestId')
                        
                        print(f"📋 Full Error Response:")
                        print(json.dumps(error_data, indent=2, ensure_ascii=False))
                        
                        # Display Request ID prominently if found
                        if request_id:
                            print(f"🔍 Request ID: {request_id}")
                            print(f"   (Use this ID when contacting VAPI support)")
                    except:
                        print(f"📋 Error Response Text: {response.text[:500]}")
                        if request_id:
                            print(f"🔍 Request ID: {request_id}")
                            print(f"   (Use this ID when contacting VAPI support)")
                
                if response.status_code in [200, 201]:
                    call_data = response.json()
                    print(f"✅ Batch call initiated successfully")

                    # Extract call IDs from response
                    call_ids = self._extract_call_ids(call_data)

                    if not call_ids:
                        print(f"❌ No call IDs found in response")
                        return None

                    print(f"📞 Found {len(call_ids)} call(s)")
                    for i, call_id in enumerate(call_ids, 1):
                        print(f"   Call {i}: {call_id}")

                    # If scheduled immediately (and not scheduled for future), monitor the calls
                    # Unless skip_wait is True (for sequential calling)
                    if schedule_immediately and not schedule_at and not skip_wait:
                        results = []

                        for i, call_id in enumerate(call_ids, 1):
                            print(f"\n📡 Monitoring call {i}/{len(call_ids)}: {call_id}")
                            # Wait for call completion and get analysis
                            final_call_data = self.wait_for_call_completion(call_id)

                            if final_call_data:
                                results.append(final_call_data)
                            else:
                                print(f"❌ Failed to get call completion data for call {i}")
                                results.append(None)

                        return results
                    else:
                        # For scheduled calls or when skip_wait=True, return call IDs immediately
                        # Return list of dicts with call IDs for later status checking
                        if skip_wait:
                            print(f"⚡ Skipping wait - returning call IDs immediately")
                        return [{'id': cid} for cid in call_ids]
                elif response.status_code >= 500:
                    # Server error - retryable
                    # Extract Request ID for logging
                    request_id = response.headers.get('X-Request-ID') or response.headers.get('Request-ID') or response.headers.get('x-request-id')
                    
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        print(f"⚠️  VAPI API server error ({response.status_code}). Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        if request_id:
                            print(f"   🔍 Request ID: {request_id}")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ VAPI API error after {max_retries} attempts: {response.status_code}")
                        if request_id:
                            print(f"🔍 Request ID: {request_id}")
                            print(f"   (Use this ID when contacting VAPI support)")
                        print(f"Response: {response.text}")
                        return None
                else:
                    # Client error (4xx) - not retryable
                    request_id = response.headers.get('X-Request-ID') or response.headers.get('Request-ID') or response.headers.get('x-request-id')
                    print(f"❌ VAPI API client error: {response.status_code}")
                    if request_id:
                        print(f"🔍 Request ID: {request_id}")
                        print(f"   (Use this ID when contacting VAPI support)")
                    print(f"Response: {response.text}")
                    return None
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️  Request timeout. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Request timeout after {max_retries} attempts")
                    return None
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️  Connection error. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Connection error after {max_retries} attempts: {e}")
                    return None
            except Exception as e:
                print(f"❌ Error making batch call: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        return None
    
    def get_recent_calls(self, limit=100):
        """
        Get recent calls from VAPI
        
        Args:
            limit (int): Maximum number of calls to retrieve
            
        Returns:
            list: List of call records
        """
        try:
            response = requests.get(
                f"{self.base_url}/call",
                headers={
                    "Authorization": f"Bearer {self.api_key}"
                },
                params={
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                calls = data.get('data', []) if isinstance(data, dict) else data
                return calls if isinstance(calls, list) else []
            else:
                print(f"❌ Failed to get recent calls: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error getting recent calls: {e}")
            return []