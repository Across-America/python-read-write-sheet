"""
STM1 Variable Mapping - Map STM1 sheet data to VAPI assistant variables
"""

def build_stm1_variable_values(customer):
    """
    Build variable values for STM1 VAPI assistant from customer data
    
    Maps STM1 sheet columns to VAPI assistant prompt variables:
    - Claim Number: book_claim_num
    - Insured Driver Name: contact_name
    - Insured/Company Name: insured_name
    - Phone: contact_phone
    - Date of Loss: (to be determined from sheet)
    - Preferred Language: (to be determined from sheet)
    
    Args:
        customer: Customer dict from STM1 sheet
        
    Returns:
        dict: Variable values for VAPI assistant
    """
    # Extract data from customer dict
    # Note: Column names are normalized (spaces -> underscores, lowercase)
    # Insured Driver Statement sheet columns:
    # - Claim Number -> claim_number
    # - Insured Driver Name -> insured_driver_name
    # - Insured Name -> insured_name_ (note: trailing underscore in normalized name)
    # - Phone Number -> phone_number
    # - Date of Loss -> date_of_loss
    # - Language -> language
    claim_number = customer.get('claim_number', '') or customer.get('book_claim_num', '')
    insured_driver_name = customer.get('insured_driver_name', '') or customer.get('contact_name', '')
    # Note: Insured Name column normalizes to 'insured_name_' (with trailing underscore)
    insured_name = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', '')
    phone_number = customer.get('phone_number', '') or customer.get('contact_phone', '')
    date_of_loss = customer.get('date_of_loss', '')
    preferred_language = customer.get('language', '') or customer.get('preferred_language', '') or 'English'
    
    # Build variable values matching VAPI assistant prompt variable names
    # The prompt uses variables like: {{INSURED_DRIVER_STATEMENT_CLAIM_NUMBER_COLUMN_ID}}
    # We provide both the exact variable name from prompt and friendly alternatives
    
    variable_values = {
        # Exact variable names from VAPI assistant prompt (with underscores)
        "INSURED_DRIVER_STATEMENT_CLAIM_NUMBER_COLUMN_ID": claim_number,
        "INSURED_DRIVER_STATEMENT_INSURED_DRIVER_NAME_COLUMN_ID": insured_driver_name,
        "INSURED_DRIVER_STATEMENT_INSURED_NAME_COLUMN_ID": insured_name,
        "INSURED_DRIVER_STATEMENT_PHONE_NUMBER_COLUMN_ID": phone_number,
        "INSURED_DRIVER_STATEMENT_DATE_OF_LOSS_COLUMN_ID": date_of_loss,
        "INSURED_DRIVER_STATEMENT_LANGUAGE_COLUMN_ID": preferred_language,
        
        # Friendly variable names (alternative formats for compatibility)
        "Claim_Number": claim_number,
        "claim_number": claim_number,
        "ClaimNumber": claim_number,
        
        "Insured_Driver_Name": insured_driver_name,
        "insured_driver_name": insured_driver_name,
        "InsuredDriverName": insured_driver_name,
        
        "Insured_Name": insured_name,
        "insured_name": insured_name,
        "InsuredName": insured_name,
        "Company": insured_name,
        "company": insured_name,
        
        "Phone_Number": phone_number,
        "phone_number": phone_number,
        "PhoneNumber": phone_number,
        
        "Date_of_Loss": date_of_loss,
        "date_of_loss": date_of_loss,
        "DateOfLoss": date_of_loss,
        
        "Preferred_Language": preferred_language,
        "preferred_language": preferred_language,
        "PreferredLanguage": preferred_language,
        "Language": preferred_language,
        "language": preferred_language,
        
        # Additional compatibility variables
        "Contact_Name": insured_driver_name,
        "contact_name": insured_driver_name,
    }
    
    return variable_values

