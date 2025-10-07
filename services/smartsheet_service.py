"""
Smartsheet Service - Handles all Smartsheet API interactions
"""

import smartsheet
from config import SMARTSHEET_ACCESS_TOKEN


class SmartsheetService:
    """Service for interacting with Smartsheet API"""
    
    def __init__(self, sheet_id):
        self.smart = smartsheet.Smartsheet(access_token=SMARTSHEET_ACCESS_TOKEN)
        self.smart.errors_as_exceptions(True)
        self.sheet_id = sheet_id
    
    def get_not_called_customers(self):
        """
        Get all customers with "Not call yet" status from cancellation dev sheet
        
        Returns:
            list: List of customer records that need to be called
        """
        try:
            print("🔍 Loading customers with 'Not call yet' status...")
            sheet = self.smart.Sheets.get_sheet(self.sheet_id)
            
            customers = []
            
            # Find column IDs
            columns = self._get_column_mapping(sheet)
            print(columns)
            # Validate required columns
            if not all([columns.get('client_id'), columns.get('policy_number'), columns.get('phone_number')]):
                print("❌ Required columns not found")
                return []
            
            if not columns.get('call_status'):
                print("❌ Call Status column not found")
                return []
            
            # Process all rows
            for row in sheet.rows:
                customer = self._process_row(row, columns)
                if customer:
                    customers.append(customer)
            
            print(f"✅ Found {len(customers)} customers with 'Not call yet' status")
            return customers
            
        except Exception as e:
            print(f"❌ Error loading customers: {e}")
            return []
    
    def update_call_status(self, customers, status="Calling"):
        """
        Update call status in Smartsheet for the customers
        
        Args:
            customers (list): List of customer records
            status (str): New status to set
        
        Returns:
            bool: Success status
        """
        try:
            print(f"📝 Updating call status to '{status}' for {len(customers)} customers...")
            
            sheet = self.smart.Sheets.get_sheet(self.sheet_id)
            
            # Find Call Status column
            call_status_col = None
            for col in sheet.columns:
                if col.title == "Call Status":
                    call_status_col = col.id
                    break
            
            if not call_status_col:
                print("❌ Call Status column not found")
                return False
            
            # Prepare rows to update
            rows_to_update = []
            
            for customer in customers:
                for row in sheet.rows:
                    if row.row_number == customer['row_number']:
                        # Create updated cell
                        new_cell = self.smart.models.Cell()
                        new_cell.column_id = call_status_col
                        new_cell.value = status
                        
                        # Create updated row
                        updated_row = self.smart.models.Row()
                        updated_row.id = row.id
                        updated_row.cells.append(new_cell)
                        
                        rows_to_update.append(updated_row)
                        break
            
            if rows_to_update:
                result = self.smart.Sheets.update_rows(self.sheet_id, rows_to_update)
                print(f"✅ Updated {len(rows_to_update)} rows in Smartsheet")
                return True
            else:
                print("❌ No rows to update")
                return False
                
        except Exception as e:
            print(f"❌ Error updating call status: {e}")
            return False
    
    def update_call_result(self, customer_info, call_data):
        """
        Update the Call Result column in Smartsheet with detailed VAPI analysis
        
        Args:
            customer_info (dict): Customer information including row_id
            call_data (dict): VAPI call data with analysis
        
        Returns:
            bool: Success status
        """
        try:
            print(f"\n📝 UPDATING SMARTSHEET WITH DETAILED CALL RESULTS")
            print("=" * 60)
            
            # Build call result string
            call_result = self._build_call_result(call_data)
            
            print(f"📊 Detailed Call Result:")
            print(f"   {call_result}")
            
            # Find Call Result column
            sheet = self.smart.Sheets.get_sheet(self.sheet_id)
            call_result_col = None
            
            for col in sheet.columns:
                if col.title == "Call Result":
                    call_result_col = col.id
                    break
            
            if not call_result_col:
                print("❌ Call Result column not found in Smartsheet")
                return False
            
            # Update the cell
            row_id = customer_info['row_id']
            
            cell = self.smart.models.Cell()
            cell.column_id = call_result_col
            cell.value = call_result
            
            row = self.smart.models.Row()
            row.id = row_id
            row.cells = [cell]
            
            result = self.smart.Sheets.update_rows(self.sheet_id, [row])
            
            if result.result:
                print(f"✅ Successfully updated Call Result in Smartsheet!")
                print(f"📝 Updated value: {call_result}")
                return True
            else:
                print(f"❌ Failed to update Smartsheet: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating Smartsheet: {e}")
            return False
    

    def _get_column_mapping(self, sheet):
        """Get column ID mapping"""
        columns = {}
        for col in sheet.columns:
            if col.title == "Client ID":
                columns['client_id'] = col.id
            elif col.title == "Policy Number":
                columns['policy_number'] = col.id
            elif col.title == "Phone number":
                columns['phone_number'] = col.id
            elif col.title == "Call Status":
                columns['call_status'] = col.id
            elif col.title == "Cancellation Date":
                columns['cancellation_date'] = col.id
            elif col.title == "Amount Due":
                columns['amount_due'] = col.id
            elif col.title == "Done?":
                columns['done?'] = col.id
            elif col.title == "F/U Date":
                columns['f_u_date'] = col.id
            elif col.title == "AI Call Summary":
                columns['ai_call_summary'] = col.id
            elif col.title == "AI Call Eval":
                columns['ai_call_eval'] = col.id
            elif col.title == "AI Call Stage":
                columns['ai_call_stage'] = col.id
            elif col.title == "Company":
                columns['company'] = col.id
            elif col.title == "Agent Name":
                columns['agent_name'] = col.id
            elif col.title == "Office":
                columns['office'] = col.id
            elif col.title == "Insured":
                columns['insured'] = col.id
            elif col.title == "LOB":
                columns['lob'] = col.id
            elif col.title == "Status":
                columns['status'] = col.id
            elif col.title == "Cancellation Reason":
                columns['cancellation_reason'] = col.id
        return columns
    
    def _process_row(self, row, columns):
        """Process a single row and return customer data if valid"""
        client_cell = row.get_column(columns['client_id'])
        policy_cell = row.get_column(columns['policy_number'])
        phone_cell = row.get_column(columns['phone_number'])
        call_status_cell = row.get_column(columns['call_status'])
        
        client_id = str(client_cell.display_value).strip() if client_cell.display_value else ""
        policy_number = str(policy_cell.display_value).strip() if policy_cell.display_value else ""
        phone_number = str(phone_cell.display_value).strip() if phone_cell.display_value else ""
        call_status = str(call_status_cell.display_value).strip() if call_status_cell.display_value else ""
        
        # Check if this customer has "Not call yet" status and valid phone number
        if (client_id and policy_number and phone_number and 
            phone_number != "No phone number" and 
            len(phone_number) >= 10 and
            call_status.lower() == "not call yet"):
            
            customer = {
                "client_id": client_id,
                "policy_number": policy_number,
                "phone_number": phone_number,
                "row_number": row.row_number,
                "row_id": row.id,
                "call_status": call_status
            }

            # Add additional customer information using pre-mapped columns
            additional_fields = {
                'agent_name': 'agent_name',
                'office': 'office',
                'insured': 'insured',
                'lob': 'lob',
                'status': 'status',
                'cancellation_reason': 'cancellation_reason',
                'cancellation_date': 'cancellation_date',
                'amount_due': 'amount_due',
                'done?': 'done?',
                'f_u_date': 'f_u_date'
            }

            for field_key, customer_key in additional_fields.items():
                if field_key in columns:
                    cell = row.get_column(columns[field_key])
                    value = str(cell.display_value) if cell.display_value else ""
                    customer[customer_key] = value

            return customer
        
        return None
    
    def _build_call_result(self, call_data):
        """Build detailed call result string from VAPI call data"""
        analysis = call_data.get('analysis', {})
        summary = analysis.get('summary', '')
        structured_data = analysis.get('structuredData', {})
        success_evaluation = analysis.get('successEvaluation', '')
        
        ended_reason = call_data.get('endedReason', '')
        duration = call_data.get('duration', 0)
        cost = call_data.get('cost', 0)
        
        call_result_parts = []
        
        # 1. Basic call status
        call_result_parts.append("CALL COMPLETED")
        
        # 2. Call summary
        if summary:
            summary_lines = summary.split('\n')
            for line in summary_lines:
                line = line.strip()
                if line and not line.startswith('**') and not line.startswith('Transfer Outcome:'):
                    clean_line = line.replace('**Call Summary:**', '').replace('**', '').strip()
                    if clean_line:
                        call_result_parts.append(f"SUMMARY: {clean_line}")
                        break
        
        # 3. Transfer status
        if structured_data and isinstance(structured_data, dict):
            call_outcome = structured_data.get('call_outcome', {})
            if call_outcome.get('transfer_requested'):
                call_result_parts.append("TRANSFER REQUESTED")
            if call_outcome.get('transfer_completed'):
                call_result_parts.append("SUCCESSFULLY TRANSFERRED")
            if call_outcome.get('customer_ended_call'):
                call_result_parts.append("CUSTOMER ENDED CALL")
        
        # 4. Customer response details
        if structured_data and isinstance(structured_data, dict):
            customer_response = structured_data.get('customer_response', {})
            payment_claimed = customer_response.get('payment_status_claimed', '')
            if payment_claimed and payment_claimed != 'not mentioned':
                call_result_parts.append(f"PAYMENT CLAIMED: {payment_claimed}")
            
            concerns = customer_response.get('concerns_raised', [])
            if concerns:
                concerns_str = ', '.join(concerns[:2])
                call_result_parts.append(f"CONCERNS: {concerns_str}")
        
        # 5. Call quality indicators
        if structured_data and isinstance(structured_data, dict):
            call_quality = structured_data.get('call_quality', {})
            if call_quality.get('customer_understood'):
                call_result_parts.append("CUSTOMER UNDERSTOOD")
            if call_quality.get('customer_engaged'):
                call_result_parts.append("CUSTOMER ENGAGED")
        
        # 6. Follow-up requirements
        if structured_data and isinstance(structured_data, dict):
            follow_up = structured_data.get('follow_up', {})
            if follow_up.get('callback_requested'):
                call_result_parts.append("CALLBACK REQUESTED")
            if follow_up.get('escalation_needed'):
                call_result_parts.append("ESCALATION NEEDED")
            
            notes = follow_up.get('notes', '')
            if notes and len(notes) > 10:
                short_notes = notes[:50] + "..." if len(notes) > 50 else notes
                call_result_parts.append(f"NOTES: {short_notes}")
        
        # 7. Success evaluation
        if success_evaluation:
            success_status = "SUCCESS" if str(success_evaluation).lower() == 'true' else "UNSUCCESSFUL"
            call_result_parts.append(f"EVALUATION: {success_status}")
        
        # 8. Call metrics
        call_result_parts.append(f"DURATION: {duration}s")
        call_result_parts.append(f"COST: ${cost:.4f}")
        
        return " | ".join(call_result_parts)

    def get_all_customers_with_stages(self):
        """
        Get all customers with their stage information (for multi-stage calling)
        
        Returns:
            list: List of customer records with all fields including stages
        """
        try:
            print("🔍 Loading all customers with stage information...")
            sheet = self.smart.Sheets.get_sheet(self.sheet_id)
            
            customers = []
            
            # Process all rows
            for row in sheet.rows:
                customer = self._extract_all_row_data(row, sheet)
                if customer:
                    customers.append(customer)
            
            print(f"✅ Loaded {len(customers)} customer records")
            return customers
            
        except Exception as e:
            print(f"❌ Error loading customers: {e}")
            return []
    
    def _extract_all_row_data(self, row, sheet):
        """
        Extract all data from a row (for stage-based processing)
        
        Args:
            row: Smartsheet row object
            sheet: Smartsheet sheet object
        
        Returns:
            dict: All customer data or None if invalid
        """
        customer = {
            "row_id": row.id,
            "row_number": row.row_number
        }
        
        # Extract all cells
        for cell in row.cells:
            # Find column title
            col_title = None
            col_type = None
            
            for col in sheet.columns:
                if col.id == cell.column_id:
                    col_title = col.title
                    col_type = col.type
                    break
            
            if col_title:
                field_name = col_title.lower().replace(" ", "_").replace("/", "_")

                # Handle checkbox columns specially
                if col_type == 'CHECKBOX':
                    value = cell.value if cell.value is not None else False
                else:
                    value = str(cell.display_value) if cell.display_value else ""
                
                customer[field_name] = value
        
        # Only return if has basic required fields for identification
        if customer.get('row_id') and customer.get('row_number'):
            return customer
        
        return None
    
    def update_customer_fields(self, customer, field_updates):
        """
        Update multiple fields for a customer
        
        Args:
            customer (dict): Customer record with row_id
            field_updates (dict): Dictionary of field_name: value pairs to update
                Supported fields: ai_call_stage, ai_summary, ai_call_eval, 
                                  followup_date, done, etc.
        
        Returns:
            bool: Success status
        """
        try:
            row_id = customer['row_id']
            
            print(f"📝 Updating row {customer.get('row_number')} with {len(field_updates)} fields...")
            
            # Get sheet and find column IDs
            sheet = self.smart.Sheets.get_sheet(self.sheet_id)
            
            # Map field names to column IDs
            column_map = {}
            for col in sheet.columns:
                field_name = col.title.lower().replace(" ", "_").replace("/", "_")
                column_map[field_name] = {'id': col.id, 'type': col.type, 'title': col.title}
            
            # Prepare cells to update
            cells_to_update = []
            
            for field_name, value in field_updates.items():
                if field_name not in column_map:
                    print(f"   ⚠️  Field '{field_name}' not found in sheet, skipping")
                    continue
                
                col_info = column_map[field_name]
                
                cell = self.smart.models.Cell()
                cell.column_id = col_info['id']
                
                # Handle different column types
                if col_info['type'] == 'CHECKBOX':
                    cell.value = bool(value)
                elif col_info['type'] == 'DATE':
                    # Ensure date is in correct format
                    cell.value = str(value) if value else None
                else:
                    cell.value = str(value) if value is not None else ""
                
                cells_to_update.append(cell)
                print(f"   • {col_info['title']}: {value}")
            
            if not cells_to_update:
                print("   ⚠️  No valid cells to update")
                return False
            
            # Create update row
            updated_row = self.smart.models.Row()
            updated_row.id = row_id
            updated_row.cells = cells_to_update
            
            # Perform update
            result = self.smart.Sheets.update_rows(self.sheet_id, [updated_row])
            
            if result.result:
                print(f"   ✅ Successfully updated {len(cells_to_update)} fields")
                return True
            else:
                print(f"   ❌ Update failed: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating customer fields: {e}")
            import traceback
            traceback.print_exc()
            return False
